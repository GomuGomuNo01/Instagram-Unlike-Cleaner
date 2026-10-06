"""Icône d'IUC dans la zone de notification de Windows (près de l'horloge).

L'application installée tourne sans fenêtre de console : cette icône permet de rouvrir
l'interface et de quitter IUC proprement (un nettoyage en cours passe alors en pause).
Dépendances de l'application Windows uniquement : pystray et Pillow (extra « package »).
"""

import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

TITLE = "IUC – Instagram Unlike Cleaner"
STARTED_MESSAGE = (
    "IUC fonctionne en arrière-plan. Son icône, près de l'horloge, permet de rouvrir "
    "l'interface ou de quitter IUC."
)


def start_tray(icon_file: Path, url: str, on_quit: Callable[[], None]) -> Any:
    """Affiche l'icône (dans son propre fil d'exécution) et renvoie-la, pour l'arrêter."""
    import pystray
    from PIL import Image

    def quit_iuc(icon: Any) -> None:
        icon.stop()
        on_quit()

    icon = pystray.Icon(
        "IUC",
        Image.open(icon_file),
        TITLE,
        pystray.Menu(
            pystray.MenuItem("Ouvrir IUC", lambda: webbrowser.open(url), default=True),
            pystray.MenuItem("Quitter IUC", quit_iuc),
        ),
    )
    icon.run_detached()
    icon.notify(STARTED_MESSAGE, TITLE)
    return icon
