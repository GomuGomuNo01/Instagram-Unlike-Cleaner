import asyncio
from typing import Annotated

import typer

from app.browser.session import (
    OUTCOME_MESSAGES,
    BrowserSession,
    BrowserStartError,
    NavigationOutcome,
)
from app.core.config import Settings, get_settings
from app.core.db import init_db, make_engine
from app.core.logs import setup_logging

app = typer.Typer(no_args_is_help=True)


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
    init_db(engine)
    engine.dispose()
    logger.info("Base locale prête : %s", settings.db_path.resolve())


@app.command()
def login(
    timeout: Annotated[
        int, typer.Option(help="Temps laissé pour se connecter, en secondes.")
    ] = 300,
    snapshot: Annotated[
        bool,
        typer.Option(help="Enregistre la structure de la page des likes (DATA_DIR/diagnostics)."),
    ] = False,
) -> None:
    """Ouvre Instagram, attend la connexion manuelle et vérifie la page des likes."""
    settings = get_settings()
    settings.ensure_dirs()
    setup_logging(settings)
    try:
        outcome = asyncio.run(_login(settings, timeout, snapshot))
    except BrowserStartError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    raise typer.Exit(0 if outcome is NavigationOutcome.OK else 1)


async def _login(settings: Settings, timeout: int, snapshot: bool) -> NavigationOutcome | None:
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
        if snapshot or outcome is NavigationOutcome.LAYOUT_CHANGED:
            report = await session.save_diagnostic(settings.diagnostics_dir, "likes")
            typer.echo(f"Diagnostic : {report}")
        if session.is_open:
            await asyncio.to_thread(input, "Appuie sur Entrée pour fermer le navigateur… ")
        return outcome
