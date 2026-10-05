"""Suppression des données locales : profil du navigateur, base, rapports, diagnostics, journaux.

Par sécurité, seuls les éléments créés par IUC sont supprimés, jamais le dossier DATA_DIR
lui-même ; et la suppression complète est refusée si ce dossier contient autre chose, au cas
où DATA_DIR désignerait par erreur un dossier personnel.
"""

import shutil
from pathlib import Path

from app.core.config import Settings


class LocalDataError(RuntimeError):
    """Suppression impossible : fichier utilisé par un autre programme, ou dossier inattendu."""


def iuc_paths(settings: Settings) -> list[Path]:
    """Tout ce qu'IUC crée dans le dossier de données."""
    db = settings.db_path
    return [
        settings.browser_profile_dir,
        db,
        db.with_name(f"{db.name}-wal"),
        db.with_name(f"{db.name}-shm"),
        settings.reports_dir,
        settings.diagnostics_dir,
        settings.logs_dir,
    ]


def unexpected_entries(settings: Settings) -> list[Path]:
    """Éléments du dossier de données qui n'ont pas été créés par IUC."""
    if not settings.data_dir.is_dir():
        return []
    known = {path.name for path in iuc_paths(settings)}
    return sorted(path for path in settings.data_dir.iterdir() if path.name not in known)


def delete_browser_profile(settings: Settings) -> bool:
    """Supprime le profil du navigateur, donc la session Instagram : il faudra se reconnecter.
    Renvoie False s'il n'existait pas."""
    return _delete(settings.browser_profile_dir)


def delete_local_data(settings: Settings) -> list[Path]:
    """Supprime toutes les données locales d'IUC et renvoie la liste des éléments supprimés."""
    unexpected = unexpected_entries(settings)
    if unexpected:
        names = ", ".join(path.name for path in unexpected)
        raise LocalDataError(
            f"Le dossier {settings.data_dir.resolve()} contient des éléments qui ne viennent "
            f"pas d'IUC ({names}) : rien n'a été supprimé. Vérifie DATA_DIR, ou déplace-les."
        )
    return [path for path in iuc_paths(settings) if _delete(path)]


def _delete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except PermissionError as exc:
        raise LocalDataError(
            f"{path} est utilisé par un autre programme. Ferme les fenêtres et commandes IUC "
            "en cours (navigateur compris), puis recommence."
        ) from exc
    return True
