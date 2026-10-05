import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated

import typer
from pydantic import ValidationError
from sqlalchemy import Engine

from app.browser.probe import ProbeError, run_probe
from app.browser.session import (
    OUTCOME_MESSAGES,
    BrowserSession,
    BrowserStartError,
    NavigationOutcome,
    SessionStatus,
)
from app.core.config import Settings, get_settings
from app.core.db import OutdatedSchemaError, init_db, make_engine
from app.core.logs import setup_logging
from app.models.schemas import CleanupFilters, ContentFilter, SortOrder
from app.models.tables import ItemStatus
from app.services.cleanup import STOP_MESSAGES, run_cleanup, today_count
from app.services.jobs import (
    RUNNABLE,
    STATUS_LABELS,
    JobActionRefused,
    JobOverview,
    job_overview,
    list_jobs,
    set_excluded,
)
from app.services.preview import (
    PreviewError,
    export_csv,
    kind_label,
    pending_items,
    run_preview,
    summarize,
)

app = typer.Typer(no_args_is_help=True)

TimeoutOption = Annotated[int, typer.Option(help="Temps laissé pour se connecter, en secondes.")]


@app.callback()
def main() -> None:
    """IUC : nettoyage local des « J'aime » Instagram."""


@app.command()
def version() -> None:
    """Affiche la version installée."""
    typer.echo("0.1.0")


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

    _run_in_browser(timeout, explore)


@app.command()
def preview(
    start: Annotated[
        datetime | None,
        typer.Option(formats=["%Y-%m-%d"], help="Likes faits à partir de cette date (AAAA-MM-JJ)."),
    ] = None,
    end: Annotated[
        datetime | None,
        typer.Option(formats=["%Y-%m-%d"], help="Likes faits jusqu'à cette date (AAAA-MM-JJ)."),
    ] = None,
    oldest_first: Annotated[
        bool, typer.Option(help="Parcourt les likes du plus ancien au plus récent.")
    ] = False,
    content: Annotated[
        ContentFilter,
        typer.Option(help="all, posts (photos et carrousels) ou reels (vidéos)."),
    ] = ContentFilter.ALL,
    author: Annotated[
        list[str] | None, typer.Option(help="Ne cible que ce compte. Option répétable.")
    ] = None,
    exclude_author: Annotated[
        list[str] | None, typer.Option(help="Ne touche jamais à ce compte. Option répétable.")
    ] = None,
    max_scanned: Annotated[
        int | None,
        typer.Option(min=1, help="Arrête la lecture après ce nombre de vignettes (essai)."),
    ] = None,
    timeout: TimeoutOption = 300,
) -> None:
    """Prépare l'aperçu d'un nettoyage : liste les likes ciblés, sans rien retirer.

    Dates et tri : filtre d'Instagram. Type et auteurs : filtrés par IUC, la version web
    d'Instagram ne proposant pas ces critères.
    """
    try:
        filters = CleanupFilters(
            sort=SortOrder.OLDEST_FIRST if oldest_first else SortOrder.NEWEST_FIRST,
            start_date=start.date() if start else None,
            end_date=end.date() if end else None,
            content=content,
            include_authors=tuple(author or ()),
            exclude_authors=tuple(exclude_author or ()),
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
        typer.echo(
            f"Aperçu n°{result.job_id} prêt : {result.targeted} likes ciblés "
            f"sur {result.scanned} lus."
        )
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
        typer.echo("Nettoyage en cours : ne clique pas dans la fenêtre. Ctrl+C pour l'interrompre.")
        result = await run_cleanup(
            session,
            engine,
            settings,
            job_id,
            account_id=status.account_id,
            max_unlikes=limit,
            snapshot=snapshot,
            on_batch=batch_done,
        )
        typer.echo(STOP_MESSAGES[result.reason])
        if result.detail:
            typer.echo(f"  Détail : {result.detail}")
        typer.echo(
            f"  Retirés : {result.done} | échecs : {result.failed} | introuvables : "
            f"{result.skipped} | restant à traiter : {result.remaining}"
        )

    try:
        _run_in_browser(timeout, clean)
    finally:
        engine.dispose()


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
    return (
        f"n°{overview.id} [{STATUS_LABELS[overview.status]}] "
        f"créé le {overview.created_at.astimezone():%d/%m/%Y %H:%M} "
        f"({period}, contenu : {filters.content}) - à traiter {overview.to_process}, "
        f"retirés {counts.get(ItemStatus.DONE, 0)}, échecs {counts.get(ItemStatus.FAILED, 0)}, "
        f"exclus {counts.get(ItemStatus.EXCLUDED, 0)}, "
        f"introuvables {counts.get(ItemStatus.SKIPPED, 0)}"
    )


LikesPageStep = Callable[[BrowserSession, Settings, SessionStatus], Awaitable[None]]


def _run_in_browser(timeout: int, on_likes_page: LikesPageStep) -> None:
    """Ouvre le navigateur, attend la connexion, ouvre la page des likes puis lance l'étape."""
    settings = get_settings()
    settings.ensure_dirs()
    setup_logging(settings)
    try:
        outcome = asyncio.run(_open_likes_page(settings, timeout, on_likes_page))
    except (BrowserStartError, ProbeError, PreviewError, JobActionRefused) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    except KeyboardInterrupt as exc:
        typer.echo("Interrompu : un nettoyage en cours est passé en pause.", err=True)
        raise typer.Exit(130) from exc
    raise typer.Exit(0 if outcome is NavigationOutcome.OK else 1)


async def _open_likes_page(
    settings: Settings, timeout: int, on_likes_page: LikesPageStep
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
        typer.echo(OUTCOME_MESSAGES[outcome])
        if outcome is NavigationOutcome.OK:
            await on_likes_page(session, settings, status)
        elif outcome is NavigationOutcome.LAYOUT_CHANGED:
            report = await session.save_diagnostic(settings.diagnostics_dir, "likes")
            typer.echo(f"Diagnostic : {report}")
        if session.is_open:
            await asyncio.to_thread(input, "Appuie sur Entrée pour fermer le navigateur… ")
        return outcome
