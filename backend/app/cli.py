import typer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """IUC : nettoyage local des « J'aime » Instagram."""


@app.command()
def version() -> None:
    """Affiche la version installée."""
    typer.echo("0.1.0")
