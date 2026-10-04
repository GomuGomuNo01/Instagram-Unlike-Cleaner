import typer

from app.core.config import get_settings
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
