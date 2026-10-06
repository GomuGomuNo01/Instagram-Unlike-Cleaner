"""Point d'entrée de l'application installée (IUC.exe, compilée avec PyInstaller).

Même programme que `iuc serve`, avec des réglages adaptés à une installation :
- données dans le dossier de l'utilisateur (%LOCALAPPDATA%\\IUC sous Windows), où se lit
  aussi un éventuel fichier .env ;
- interface compilée embarquée dans l'application ;
- navigateur déjà installé (Google Chrome, sinon Microsoft Edge) plutôt qu'un Chromium
  embarqué de 150 Mo ;
- aucune fenêtre de console : une icône près de l'horloge rouvre l'interface ou quitte IUC,
  et relancer IUC.exe rouvre simplement l'interface déjà lancée.
Chaque réglage reste modifiable par une variable d'environnement ou le fichier .env.
"""

import logging
import os
import sys
import webbrowser
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

DESKTOP_BROWSERS = '["chrome", "msedge"]'

logger = logging.getLogger(__name__)


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


def silence_missing_streams() -> None:
    """Sans console, sys.stdout et sys.stderr valent None : les messages et journaux qui y
    sont écrits partent alors vers nulle part (le journal reste dans DATA_DIR/logs)."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


# Verrou nommé de Windows, gardé ouvert tant qu'IUC tourne : un second IUC.exe le trouve
# déjà pris. Aucune connexion réseau (le backend n'en ouvre jamais, voir test_security).
INSTANCE_LOCK = r"Local\IUC-Instagram-Unlike-Cleaner"
_ERROR_ALREADY_EXISTS = 183
_held_locks: list[int] = []


def first_instance(name: str = INSTANCE_LOCK) -> bool:
    """Vrai pour le premier IUC.exe lancé par cet utilisateur ; toujours vrai hors Windows."""
    if sys.platform != "win32":
        return True
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.CreateMutexW(None, False, name)
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    _held_locks.append(handle)  # libéré par Windows à la fin du programme
    return True


def show_error(message: str) -> None:
    """Affiche une erreur : fenêtre Windows dans l'application, sortie d'erreur ailleurs."""
    logger.error(message)
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "IUC", 0x10)  # icône « erreur »
    else:
        print(message, file=sys.stderr)


def main() -> None:
    silence_missing_streams()
    # Fichiers embarqués par PyInstaller : dans sys._MEIPASS une fois compilé.
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    os.chdir(configure(bundle))  # le fichier .env éventuel se lit dans ce dossier

    from app.cli import run_server
    from app.core.config import get_settings
    from app.tray import start_tray

    settings = get_settings()
    url = f"http://127.0.0.1:{settings.api_port}"
    if not first_instance():
        webbrowser.open(url)  # IUC tourne déjà : on rouvre simplement son interface
        return

    tray: Any = None

    def with_tray(server: Any) -> None:
        nonlocal tray

        def stop_server() -> None:
            server.should_exit = True  # arrêt propre : un nettoyage en cours passe en pause

        tray = start_tray(bundle / "iuc.ico", url, stop_server)

    try:
        started = run_server(settings, open_ui=True, on_server=with_tray)
    except Exception as exc:
        show_error(f"IUC s'est arrêté sur une erreur inattendue : {exc}")
        raise
    finally:
        if tray is not None:
            tray.stop()
    if not started:
        show_error(
            f"IUC n'a pas pu démarrer : le port {settings.api_port} est déjà utilisé par un "
            "autre programme. Choisis-en un autre avec API_PORT dans le fichier .env du "
            f"dossier {Path.cwd()}."
        )


if __name__ == "__main__":
    main()
