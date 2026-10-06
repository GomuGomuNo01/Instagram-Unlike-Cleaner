"""Point d'entrée de l'application installée (IUC.exe, compilée avec PyInstaller).

Même programme que `iuc serve`, avec des réglages adaptés à une installation :
- données dans le dossier de l'utilisateur (%LOCALAPPDATA%\\IUC sous Windows), où se lit
  aussi un éventuel fichier .env ;
- interface compilée embarquée dans l'application ;
- navigateur déjà installé (Google Chrome, sinon Microsoft Edge) plutôt qu'un Chromium
  embarqué de 150 Mo.
Chaque réglage reste modifiable par une variable d'environnement ou le fichier .env.
"""

import os
import sys
from collections.abc import MutableMapping
from pathlib import Path

DESKTOP_BROWSERS = '["chrome", "msedge"]'


def user_data_root(environ: MutableMapping[str, str] = os.environ) -> Path:
    """Dossier propre à l'utilisateur : %LOCALAPPDATA%\\IUC, ~/.local/share/IUC ailleurs."""
    base = environ.get("LOCALAPPDATA") or environ.get("XDG_DATA_HOME")
    return (Path(base) if base else Path.home() / ".local" / "share") / "IUC"


def configure(bundle: Path, environ: MutableMapping[str, str] = os.environ) -> Path:
    """Prépare l'environnement de l'application installée ; renvoie le dossier de travail."""
    root = user_data_root(environ)
    root.mkdir(parents=True, exist_ok=True)
    environ.setdefault("DATA_DIR", str(root / "data"))
    environ.setdefault("FRONTEND_DIST", str(bundle / "frontend" / "dist"))
    environ.setdefault("BROWSER_CHANNELS", DESKTOP_BROWSERS)
    return root


def main() -> None:
    # Fichiers embarqués par PyInstaller : dans sys._MEIPASS une fois compilé.
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    os.chdir(configure(bundle))  # le fichier .env éventuel se lit dans ce dossier

    from app.cli import app

    app(["serve"], prog_name="IUC")


if __name__ == "__main__":
    main()
