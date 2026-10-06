import asyncio
import json
import signal
import tempfile
import webbrowser
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from types import FrameType
from typing import Annotated

import typer
import uvicorn
from pydantic import ValidationError
from sqlalchemy import Engine

from app.api.security import TOKEN_HEADER, new_token
from app.browser.probe import ProbeError, run_probe
from app.browser.session import (
    BrowserSession,
    BrowserStartError,
    NavigationOutcome,
    SessionStatus,
)
from app.core.codespaces import forwarded_host
from app.core.config import Settings, get_settings
from app.core.db import OutdatedSchemaError, init_db, make_engine
from app.core.logs import setup_logging
from app.main import create_app
from app.models.schemas import CleanupFilters, SortOrder
from app.models.tables import ItemStatus, JobStatus
from app.services.cleanup import STOP_MESSAGES, CleanupControl, run_cleanup, today_count
from app.services.jobs import (
    RUNNABLE,
    STATUS_LABELS,
    JobActionRefused,
    JobOverview,
    job_overview,
    list_jobs,
    set_excluded,
    stop_job,
)
from app.services.local_data import (
    LocalDataError,
    delete_browser_profile,
    delete_local_data,
    unexpected_entries,
)
from app.services.preview import (
    PreviewError,
    export_csv,
    kind_label,
    pending_items,
    run_preview,
    summarize,
)
from app.services.report import (
    ITEM_STATUS_LABELS,
    build_report,
    summary_lines,
    write_report_files,
)

app = typer.Typer(no_args_is_help=True)

TimeoutOption = Annotated[int, typer.Option(help="Temps laissé pour se connecter, en secondes.")]
# Nombre d'échecs détaillés par `iuc report` ; la liste complète est dans le CSV.
_MAX_PROBLEMS_SHOWN = 20


@app.callback()
def main() -> None:
    """IUC : nettoyage local des « J'aime » Instagram."""


@app.command()
def version() -> None:
    """Affiche la version installée."""
    typer.echo("0.1.0")


@app.command()
def serve(
    port: Annotated[
        int | None,
        typer.Option(min=1024, max=65535, help="Port de l'API (par défaut : API_PORT, 8765)."),
    ] = None,
    open_ui: Annotated[
        bool, typer.Option("--open/--no-open", help="Ouvre l'interface dans le navigateur.")
    ] = True,
) -> None:
    """Lance l'API locale et l'interface, sur 127.0.0.1 uniquement."""
    settings = get_settings()
    if port is not None:
        settings = settings.model_copy(update={"api_port": port})
    settings.ensure_dirs()
    setup_logging(settings)
    port = settings.api_port
    token = new_token()
    api = create_app(settings, token=token)
    url = f"http://127.0.0.1:{port}"
    typer.echo(f"Interface : {url}")
    if public_host := forwarded_host(port):
        typer.echo(f"Dans ce Codespace : https://{public_host}")
    if settings.api_docs:
        typer.echo(f"Documentation de l'API : {url}/docs (chargée depuis un CDN)")
    typer.echo(f"Jeton de l'API (en-tête {TOKEN_HEADER}) : {token}")
    typer.echo("Ctrl+C pour arrêter le serveur : un nettoyage en cours passe en pause.")
    # Journal d'accès désactivé : il afficherait le jeton passé dans l'URL du flux SSE.
    config = uvicorn.Config(api, host="127.0.0.1", port=port, access_log=False, log_level="warning")
    server = uvicorn.Server(config)

    async def run_server() -> None:
        async def open_when_ready() -> None:
            while not server.started:
                await asyncio.sleep(0.1)
            webbrowser.open(url)

        opener = asyncio.create_task(open_when_ready()) if open_ui else None
        await server.serve()
        if opener is not None:
            opener.cancel()

    # asyncio.run utilise sous Windows la boucle Proactor, nécessaire à Playwright.
    asyncio.run(run_server())


@app.command()
def openapi(
    output: Annotated[Path, typer.Argument(help="Fichier JSON à écrire.")],
) -> None:
    """Exporte le schéma OpenAPI de l'API (sert à générer les types du frontend)."""
    with tempfile.TemporaryDirectory() as data_dir:
        api = create_app(Settings(_env_file=None, data_dir=Path(data_dir)), token="export")
        schema = api.openapi()
        api.state.iuc.engine.dispose()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    typer.echo(f"Schéma OpenAPI écrit : {output}")


@app.command()
def init() -> None:
    """Prépare le dossier de données local et la base SQLite."""
    settings = get_settings()
    settings.ensure_dirs()
    logger = setup_logging(settings)
    engine = make_engine(settings.db_path)
    try:
        init_db(engine)
    except OutdatedSchemaError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    finally:
        engine.dispose()
    logger.info("Base locale prête : %s", settings.db_path.resolve())


@app.command()
def login(
    timeout: TimeoutOption = 300,
    snapshot: Annotated[
        bool,
        typer.Option(help="Enregistre la structure de la page des likes (DATA_DIR/diagnostics)."),
    ] = False,
) -> None:
    """Ouvre Instagram, attend la connexion manuelle et vérifie la page des likes."""

    async def after_likes_page(
        session: BrowserSession, settings: Settings, _status: SessionStatus
    ) -> None:
        if snapshot:
            report = await session.save_diagnostic(settings.diagnostics_dir, "likes")
            typer.echo(f"Diagnostic : {report}")

    _run_in_browser(timeout, after_likes_page)


@app.command()
def probe(timeout: TimeoutOption = 300) -> None:
    """Explore la page des likes (filtres, mode sélection) sans rien retirer."""

    async def explore(session: BrowserSession, settings: Settings, _status: SessionStatus) -> None:
        typer.echo(
            "Exploration en cours : ne clique pas dans la fenêtre. Aucun like ne sera retiré."
        )
        reports = await run_probe(session, settings.diagnostics_dir)
        typer.echo("Diagnostics enregistrés :")
        for report in reports:
            typer.echo(f"  {report}")

    # L'exploration sert justement à étudier une interface d'Instagram qui a changé.
    _run_in_browser(timeout, explore, explore_changed_layout=True)


_INSTAGRAM_PANEL = "Filtre d'Instagram (panneau « Trier et filtrer »)"


@app.command()
def preview(
    oldest_first: Annotated[
        bool,
        typer.Option(
            help="Trier par : du plus ancien au plus récent (par défaut : du plus récent).",
            rich_help_panel=_INSTAGRAM_PANEL,
        ),
    ] = False,
    start: Annotated[
        datetime | None,
        typer.Option(
            formats=["%Y-%m-%d"],
            help="Date de début : likes faits à partir de ce jour (AAAA-MM-JJ).",
            rich_help_panel=_INSTAGRAM_PANEL,
        ),
    ] = None,
    end: Annotated[
        datetime | None,
        typer.Option(
            formats=["%Y-%m-%d"],
            help="Date de fin : likes faits jusqu'à ce jour (AAAA-MM-JJ).",
            rich_help_panel=_INSTAGRAM_PANEL,
        ),
    ] = None,
    max_scanned: Annotated[
        int | None,
        typer.Option(min=1, help="Arrête la lecture après ce nombre de vignettes (essai)."),
    ] = None,
    timeout: TimeoutOption = 300,
) -> None:
    """Prépare l'aperçu d'un nettoyage : liste les likes ciblés, sans rien retirer.

    Les critères sont ceux du filtre d'Instagram web, dans son panneau « Trier et filtrer » :
    tri, date de début et date de fin du like. Pour garder un like, exclus-le ensuite de
    l'aperçu avec `iuc exclude`.
    """
    try:
        filters = CleanupFilters(
            sort=SortOrder.OLDEST_FIRST if oldest_first else SortOrder.NEWEST_FIRST,
            start_date=start.date() if start else None,
            end_date=end.date() if end else None,
        )
    except ValidationError as exc:
        messages = "; ".join(
            str(error["msg"]).removeprefix("Value error, ") for error in exc.errors()
        )
        typer.echo(f"Critères invalides : {messages}", err=True)
        raise typer.Exit(2) from exc

    engine = _open_database()

    async def collect(session: BrowserSession, settings: Settings, status: SessionStatus) -> None:
        typer.echo(
            "Collecte de l'aperçu : ne clique pas dans la fenêtre. Aucun like ne sera retiré."
        )
        result = await run_preview(
            session,
            engine,
            filters,
            account_id=status.account_id,
            max_scanned=max_scanned,
            on_progress=lambda count: typer.echo(f"\r  {count} vignettes lues", nl=False),
        )
        typer.echo("")
        items = pending_items(engine, result.job_id)
        summary = summarize(items)
        report = export_csv(items, settings.reports_dir / f"apercu-{result.job_id}.csv")
        typer.echo(f"Aperçu n°{result.job_id} prêt : {result.targeted} likes ciblés.")
        if summary.total:
            kinds = ", ".join(
                f"{kind_label(kind)} {count}" for kind, count in summary.by_kind.items()
            )
            authors = ", ".join(f"@{name} ({count})" for name, count in summary.top_authors)
            typer.echo(f"  Par type : {kinds}")
            typer.echo(f"  Auteurs les plus présents : {authors}")
        typer.echo(f"  Liste complète : {report}")
        typer.echo("Rien n'a été retiré.")

    try:
        _run_in_browser(timeout, collect)
    finally:
        engine.dispose()


@app.command()
def jobs() -> None:
    """Liste les nettoyages enregistrés et leur avancement."""
    engine = _open_database()
    try:
        overviews = list_jobs(engine)
        if not overviews:
            typer.echo("Aucun nettoyage enregistré. Commence par `iuc preview`.")
        for overview in overviews:
            typer.echo(_describe(overview))
        daily_limit = get_settings().daily_limit
        typer.echo(f"Unlikes tentés aujourd'hui : {today_count(engine)} / {daily_limit}")
    finally:
        engine.dispose()


@app.command()
def exclude(
    job_id: Annotated[int, typer.Argument(help="Numéro du nettoyage (voir `iuc jobs`).")],
    rank: Annotated[
        list[int] | None, typer.Option(help="Rang dans le CSV d'aperçu. Option répétable.")
    ] = None,
    author: Annotated[
        list[str] | None, typer.Option(help="Tous les likes de ce compte. Option répétable.")
    ] = None,
    restore: Annotated[
        bool, typer.Option(help="Remet les likes désignés dans le nettoyage.")
    ] = False,
) -> None:
    """Exclut des likes de l'aperçu (ou les y remet) : ils ne seront jamais retirés."""
    if not rank and not author:
        typer.echo("Indique au moins un --rank ou un --author.", err=True)
        raise typer.Exit(2)
    engine = _open_database()
    try:
        changed = set_excluded(
            engine, job_id, ranks=list(rank or ()), authors=list(author or ()), restore=restore
        )
    except JobActionRefused as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    finally:
        engine.dispose()
    action = "remis dans le nettoyage" if restore else "exclus"
    typer.echo(f"{changed} likes {action} (nettoyage n°{job_id}).")


@app.command()
def run(
    job_id: Annotated[int, typer.Argument(help="Numéro du nettoyage (voir `iuc jobs`).")],
    limit: Annotated[
        int | None,
        typer.Option(min=1, help="Nombre maximal de likes à retirer pendant cette exécution."),
    ] = None,
    snapshot: Annotated[
        bool, typer.Option(help="Enregistre un diagnostic avant et après chaque lot.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Ne demande pas de confirmation.")] = False,
    timeout: TimeoutOption = 300,
) -> None:
    """Lance ou reprend un nettoyage : retire les likes validés de l'aperçu, par lots.

    Le premier lancement valide l'aperçu. Le nettoyage passe en pause à la limite
    quotidienne, au nombre demandé par --limit, ou au moindre signal d'Instagram.
    """
    settings = get_settings()
    engine = _open_database()
    overview = job_overview(engine, job_id)
    if overview is None or overview.status not in RUNNABLE:
        engine.dispose()
        state = "inexistant" if overview is None else f"« {STATUS_LABELS[overview.status]} »"
        typer.echo(f"Le nettoyage n°{job_id} est {state} : rien à lancer.", err=True)
        raise typer.Exit(1)
    planned = overview.to_process if limit is None else min(limit, overview.to_process)
    left_today = max(settings.daily_limit - today_count(engine), 0)
    typer.echo(_describe(overview))
    if not yes and not typer.confirm(
        f"Retirer jusqu'à {planned} likes maintenant (limite du jour : {left_today} restants) ? "
        "Cette action modifie ton compte Instagram.",
        default=False,
    ):
        engine.dispose()
        typer.echo("Rien n'a été retiré.")
        raise typer.Exit(1)

    def batch_done(removed: int, total: int) -> None:
        typer.echo(f"  Lot retiré : {removed} likes (total : {total})")

    async def clean(session: BrowserSession, settings: Settings, status: SessionStatus) -> None:
        typer.echo(
            "Nettoyage en cours : ne clique pas dans la fenêtre. Ctrl+C pour le mettre en pause."
        )
        control = CleanupControl()
        loop = asyncio.get_running_loop()
        task = asyncio.current_task()
        interrupts = 0

        def on_interrupt(_signum: int, _frame: FrameType | None) -> None:
            # Premier Ctrl+C : pause après le lot en cours, contrôlé et enregistré.
            # Second Ctrl+C : interruption immédiate (le nettoyage passe tout de même en pause).
            nonlocal interrupts
            interrupts += 1
            if interrupts == 1:
                typer.echo(
                    "\nPause demandée : le lot en cours se termine et sera contrôlé. "
                    "Ctrl+C à nouveau pour interrompre immédiatement."
                )
                loop.call_soon_threadsafe(control.request_pause)
            elif task is not None:
                loop.call_soon_threadsafe(task.cancel)

        previous_handler = signal.signal(signal.SIGINT, on_interrupt)
        try:
            result = await run_cleanup(
                session,
                engine,
                settings,
                job_id,
                account_id=status.account_id,
                max_unlikes=limit,
                snapshot=snapshot,
                on_batch=batch_done,
                control=control,
            )
        finally:
            signal.signal(signal.SIGINT, previous_handler)
        typer.echo(STOP_MESSAGES[result.reason])
        if result.detail:
            typer.echo(f"  Détail : {result.detail}")
        typer.echo(
            f"  Retirés : {result.done} | échecs : {result.failed} | introuvables : "
            f"{result.skipped} | restant à traiter : {result.remaining}"
        )
        overview = job_overview(engine, job_id)
        if overview is not None and overview.status in (JobStatus.COMPLETED, JobStatus.STOPPED):
            csv_path, _ = write_report_files(engine, settings.reports_dir, job_id)
            typer.echo(f"  Rapport final : {csv_path}")
        else:
            typer.echo(f"  Bilan à tout moment : iuc report {job_id}")

    try:
        _run_in_browser(timeout, clean)
    finally:
        engine.dispose()


@app.command()
def stop(
    job_id: Annotated[int, typer.Argument(help="Numéro du nettoyage (voir `iuc jobs`).")],
    yes: Annotated[bool, typer.Option("--yes", help="Ne demande pas de confirmation.")] = False,
) -> None:
    """Arrête définitivement un nettoyage : les likes non traités ne seront pas retirés.

    Un nettoyage en cours d'exécution dans un autre terminal s'arrête après son lot en cours.
    Pour une simple pause, utilise plutôt Ctrl+C pendant `iuc run`.
    """
    if not yes and not typer.confirm(
        f"Arrêter définitivement le nettoyage n°{job_id} ? Il ne pourra pas être repris.",
        default=False,
    ):
        typer.echo("Nettoyage non arrêté.")
        raise typer.Exit(1)
    engine = _open_database()
    try:
        previous = stop_job(engine, job_id)
    except JobActionRefused as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    finally:
        engine.dispose()
    typer.echo(f"Nettoyage n°{job_id} arrêté.")
    if previous is JobStatus.RUNNING:
        typer.echo("S'il est en cours d'exécution, il s'arrêtera après son lot en cours.")


@app.command()
def report(
    job_id: Annotated[int, typer.Argument(help="Numéro du nettoyage (voir `iuc jobs`).")],
) -> None:
    """Affiche le bilan d'un nettoyage et l'exporte en CSV et en JSON (DATA_DIR/reports)."""
    settings = get_settings()
    engine = _open_database()
    try:
        job_report = build_report(engine, job_id)
        csv_path, json_path = write_report_files(engine, settings.reports_dir, job_id)
    except JobActionRefused as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    finally:
        engine.dispose()
    for line in summary_lines(job_report):
        typer.echo(line)
    problems = job_report.problems
    if problems:
        typer.echo("  Échecs et likes introuvables :")
        for problem in problems[:_MAX_PROBLEMS_SHOWN]:
            author = f"@{problem.author}" if problem.author else "auteur inconnu"
            typer.echo(
                f"    rang {problem.rank}, {author} : {ITEM_STATUS_LABELS[problem.status]}"
                + (f" ({problem.detail})" if problem.detail else "")
            )
        if len(problems) > _MAX_PROBLEMS_SHOWN:
            typer.echo(f"    … et {len(problems) - _MAX_PROBLEMS_SHOWN} autres, voir le CSV.")
    typer.echo(f"  Détail : {csv_path}")
    typer.echo(f"  JSON : {json_path}")


@app.command()
def logout(
    yes: Annotated[bool, typer.Option("--yes", help="Ne demande pas de confirmation.")] = False,
) -> None:
    """Supprime le profil du navigateur, donc ta session Instagram : il faudra te reconnecter.

    Les nettoyages, rapports et journaux sont conservés.
    """
    settings = get_settings()
    if not yes and not typer.confirm(
        f"Supprimer le profil du navigateur ({settings.browser_profile_dir.resolve()}) ? "
        "Tu devras te reconnecter à Instagram.",
        default=False,
    ):
        typer.echo("Rien n'a été supprimé.")
        raise typer.Exit(1)
    try:
        deleted = delete_browser_profile(settings)
    except LocalDataError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if deleted:
        typer.echo("Profil du navigateur supprimé : IUC n'est plus connecté à Instagram.")
    else:
        typer.echo("Aucun profil de navigateur à supprimer.")


@app.command()
def purge(
    yes: Annotated[bool, typer.Option("--yes", help="Ne demande pas de confirmation.")] = False,
) -> None:
    """Supprime toutes les données locales d'IUC : profil du navigateur, base (nettoyages et
    historique), rapports, diagnostics et journaux. Le fichier .env est conservé."""
    settings = get_settings()
    data_dir = settings.data_dir.resolve()
    if unexpected_entries(settings):
        # Vérifié avant la question, pour ne pas faire confirmer une suppression refusée.
        try:
            delete_local_data(settings)
        except LocalDataError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
    if not yes and not typer.confirm(
        f"Supprimer définitivement toutes les données d'IUC dans {data_dir} ? "
        "L'historique des nettoyages sera perdu.",
        default=False,
    ):
        typer.echo("Rien n'a été supprimé.")
        raise typer.Exit(1)
    try:
        deleted = delete_local_data(settings)
    except LocalDataError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if not deleted:
        typer.echo("Aucune donnée locale à supprimer.")
    for path in deleted:
        typer.echo(f"Supprimé : {path}")
    if deleted:
        # Trace dans le nouveau journal : l'ancien vient d'être supprimé avec le reste.
        setup_logging(settings).warning(
            "Données locales supprimées avec `iuc purge` (%d éléments)", len(deleted)
        )


def _open_database() -> Engine:
    settings = get_settings()
    settings.ensure_dirs()
    engine = make_engine(settings.db_path)
    try:
        init_db(engine)
    except OutdatedSchemaError as exc:
        engine.dispose()
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    return engine


def _describe(overview: JobOverview) -> str:
    counts = overview.counts
    filters = overview.filters
    if filters.start_date or filters.end_date:
        period = f"likes du {filters.start_date or 'début'} au {filters.end_date or 'jour'}"
    else:
        period = "toutes dates"
    order = (
        "du plus ancien au plus récent"
        if filters.sort is SortOrder.OLDEST_FIRST
        else "du plus récent au plus ancien"
    )
    return (
        f"n°{overview.id} [{STATUS_LABELS[overview.status]}] "
        f"créé le {overview.created_at.astimezone():%d/%m/%Y %H:%M} "
        f"({period}, {order}) - à traiter {overview.to_process}, "
        f"retirés {counts.get(ItemStatus.DONE, 0)}, échecs {counts.get(ItemStatus.FAILED, 0)}, "
        f"exclus {counts.get(ItemStatus.EXCLUDED, 0)}, "
        f"introuvables {counts.get(ItemStatus.SKIPPED, 0)}"
    )


LikesPageStep = Callable[[BrowserSession, Settings, SessionStatus], Awaitable[None]]


def _run_in_browser(
    timeout: int, on_likes_page: LikesPageStep, *, explore_changed_layout: bool = False
) -> None:
    """Ouvre le navigateur, attend la connexion, ouvre la page des likes puis lance l'étape.

    `explore_changed_layout` : lance aussi l'étape si l'interface d'Instagram a changé.
    """
    settings = get_settings()
    settings.ensure_dirs()
    setup_logging(settings)
    try:
        outcome = asyncio.run(
            _open_likes_page(settings, timeout, on_likes_page, explore_changed_layout)
        )
    except (BrowserStartError, ProbeError, PreviewError, JobActionRefused) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    except (KeyboardInterrupt, asyncio.CancelledError) as exc:
        typer.echo("Interrompu : un nettoyage en cours est passé en pause.", err=True)
        raise typer.Exit(130) from exc
    raise typer.Exit(0 if outcome is NavigationOutcome.OK else 1)


async def _open_likes_page(
    settings: Settings,
    timeout: int,
    on_likes_page: LikesPageStep,
    explore_changed_layout: bool,
) -> NavigationOutcome | None:
    async with BrowserSession(settings.browser_profile_dir) as session:
        await session.open_home()
        status = await session.status()
        if not status.logged_in:
            typer.echo(
                "Connecte-toi dans la fenêtre Chromium (2FA comprise). "
                "Le script ne lit aucun champ du formulaire."
            )
            status = await session.wait_for_login(timeout)
        if not status.logged_in:
            typer.echo("Connexion non détectée : délai dépassé ou fenêtre fermée.", err=True)
            return None
        typer.echo(f"Connecté (identifiant du compte : {status.account_id or 'inconnu'}).")

        outcome = await session.open_likes_page()
        typer.echo(session.describe(outcome))
        layout_changed = outcome is NavigationOutcome.LAYOUT_CHANGED
        if outcome is NavigationOutcome.OK or (layout_changed and explore_changed_layout):
            await on_likes_page(session, settings, status)
        elif layout_changed:
            report = await session.save_diagnostic(settings.diagnostics_dir, "likes")
            typer.echo(f"Diagnostic : {report}")
        if session.is_open:
            await asyncio.to_thread(input, "Appuie sur Entrée pour fermer le navigateur… ")
        return outcome
