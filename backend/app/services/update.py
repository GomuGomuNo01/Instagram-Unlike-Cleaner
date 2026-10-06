"""Mise à jour de l'application Windows depuis les Releases GitHub du projet.

Seul module du backend autorisé à ouvrir une connexion (voir test_security), pour deux
requêtes anonymes en lecture, sans cookie ni identifiant, qui n'envoient rien d'autre
qu'elles-mêmes :
- la lecture de la Release la plus récente sur l'API publique de GitHub ;
- sur demande de l'utilisateur, le téléchargement de son installeur, dont la taille et
  l'empreinte SHA-256 publiées par GitHub sont vérifiées avant de le lancer.
L'installeur attend la fermeture d'IUC, remplace l'application, puis la relance ; les
données (DATA_DIR) ne sont pas touchées. Activée par l'application Windows (UPDATE_CHECK).
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import subprocess
import sys
import time
import urllib.request
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Literal

from app import __version__
from app.core.config import Settings

logger = logging.getLogger(__name__)

REPOSITORY = "GomuGomuNo01/Instagram-Unlike-Cleaner"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASE_PAGE = f"https://github.com/{REPOSITORY}/releases/latest"
# Seules adresses de téléchargement acceptées : les fichiers des Releases du projet.
DOWNLOAD_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"
INSTALLER = "IUC-Setup.exe"
PORTABLE_DOWNLOAD = f"{RELEASE_PAGE}/download/IUC-portable.zip"
# Installation silencieuse ; /UPDATE=1 fait attendre la fermeture d'IUC, puis le relance
# (packaging/iuc.iss).
INSTALLER_ARGS = ("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/UPDATE=1")
CHECK_INTERVAL = 6 * 3600  # secondes : une lecture de GitHub toutes les six heures au plus
TIMEOUT = 20  # secondes sans réponse avant d'abandonner
CHUNK = 1 << 20

# Comment IUC a été installé, donc comment le mettre à jour.
InstallMode = Literal["installer", "portable", "source"]
Opener = Callable[[urllib.request.Request], AbstractContextManager[IO[bytes]]]


class UpdateError(Exception):
    """Vérification ou téléchargement impossible : le message s'affiche tel quel."""


class UpdateRefused(UpdateError):
    """Mise à jour impossible dans la situation actuelle (déjà à jour, version portable...)."""


def parse_version(text: str) -> tuple[int, ...]:
    parts = text.strip().removeprefix("v").split(".")
    if not all(part.isdigit() for part in parts):
        raise UpdateError(f"Numéro de version illisible : {text!r}.")
    return tuple(int(part) for part in parts)


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


@dataclass(frozen=True)
class Asset:
    url: str
    size: int
    sha256: str | None


@dataclass(frozen=True)
class Release:
    version: str
    installer: Asset | None


def parse_release(payload: object) -> Release:
    """Extrait d'une réponse de l'API de GitHub la version et l'installeur publiés."""
    if not isinstance(payload, dict) or not isinstance(payload.get("tag_name"), str):
        raise UpdateError("Réponse inattendue de GitHub.")
    version = payload["tag_name"].removeprefix("v")
    parse_version(version)
    installer = None
    for asset in payload.get("assets") or []:
        if isinstance(asset, dict) and asset.get("name") == INSTALLER:
            digest = asset.get("digest")
            installer = Asset(
                url=str(asset.get("browser_download_url", "")),
                size=int(asset.get("size", 0)),
                sha256=digest.removeprefix("sha256:").lower()
                if isinstance(digest, str) and digest.startswith("sha256:")
                else None,
            )
    return Release(version=version, installer=installer)


def _request(url: str, accept: str) -> urllib.request.Request:
    # Requête anonyme en lecture : ni corps, ni cookie, ni identifiant.
    return urllib.request.Request(
        url, headers={"Accept": accept, "User-Agent": f"IUC/{__version__}"}, method="GET"
    )


def _open(request: urllib.request.Request) -> AbstractContextManager[IO[bytes]]:
    response: AbstractContextManager[IO[bytes]] = urllib.request.urlopen(request, timeout=TIMEOUT)
    return response


def fetch_latest(opener: Opener = _open) -> Release:
    try:
        with opener(_request(LATEST_RELEASE_API, "application/vnd.github+json")) as response:
            payload = json.load(response)
    except OSError as exc:
        raise UpdateError(
            "GitHub ne répond pas : impossible de vérifier les mises à jour pour le moment."
        ) from exc
    except ValueError as exc:
        raise UpdateError("Réponse illisible de GitHub.") from exc
    return parse_release(payload)


def remove_downloads(folder: Path) -> None:
    """Supprime les installeurs déjà téléchargés (un installeur encore ouvert est ignoré)."""
    for path in folder.glob("IUC-Setup-*"):
        with contextlib.suppress(OSError):
            path.unlink()


def download(release: Release, folder: Path, opener: Opener = _open) -> Path:
    """Télécharge l'installeur de `release` et vérifie sa taille et son empreinte SHA-256."""
    asset = release.installer
    if asset is None:
        raise UpdateError(f"La version {release.version} ne contient pas d'installeur.")
    if not asset.url.startswith(DOWNLOAD_PREFIX):
        raise UpdateError("Adresse de téléchargement inattendue : mise à jour refusée.")
    if asset.sha256 is None:
        raise UpdateError("GitHub ne publie pas l'empreinte de l'installeur : mise à jour refusée.")
    remove_downloads(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"IUC-Setup-{release.version}.exe"
    partial = folder / f"{target.name}.part"
    digest = hashlib.sha256()
    try:
        with (
            opener(_request(asset.url, "application/octet-stream")) as response,
            partial.open("wb") as file,
        ):
            while chunk := response.read(CHUNK):
                digest.update(chunk)
                file.write(chunk)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise UpdateError("Téléchargement interrompu : réessaie dans un moment.") from exc
    if partial.stat().st_size != asset.size or digest.hexdigest() != asset.sha256:
        partial.unlink()
        raise UpdateError(
            "L'installeur téléchargé ne correspond pas à celui publié : il a été supprimé, "
            "rien n'a été installé."
        )
    partial.replace(target)
    return target


def launch_installer(installer: Path) -> None:
    """Lance l'installeur, détaché d'IUC pour lui survivre."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    subprocess.Popen([str(installer), *INSTALLER_ARGS], creationflags=flags, close_fds=True)


def detect_mode(executable: Path | None = None, *, frozen: bool | None = None) -> InstallMode:
    """Application installée (désinstalleur d'Inno Setup à côté d'IUC.exe), version portable,
    ou code source lancé avec `iuc serve`."""
    if not (getattr(sys, "frozen", False) if frozen is None else frozen):
        return "source"
    folder = Path(executable or sys.executable).parent
    return "installer" if (folder / "unins000.exe").exists() else "portable"


@dataclass(frozen=True)
class UpdateStatus:
    enabled: bool
    mode: InstallMode
    current: str
    latest: str | None = None
    error: str | None = None

    @property
    def available(self) -> bool:
        return self.latest is not None and is_newer(self.latest, self.current)


class Updater:
    """Vérifie et applique les mises à jour ; une seule lecture de GitHub par CHECK_INTERVAL."""

    def __init__(
        self,
        settings: Settings,
        *,
        mode: InstallMode,
        current: str = __version__,
        opener: Opener = _open,
        launcher: Callable[[Path], None] = launch_installer,
    ) -> None:
        self.settings = settings
        self.mode = mode
        self.current = current
        self._opener = opener
        self._launcher = launcher
        self._release: Release | None = None
        self._checked_at = 0.0
        self._installing = False

    async def status(self) -> UpdateStatus:
        if not self.settings.update_check:
            return UpdateStatus(enabled=False, mode=self.mode, current=self.current)
        try:
            release = await self._latest()
        except UpdateError as exc:
            logger.info("Vérification des mises à jour impossible : %s", exc)
            return UpdateStatus(True, self.mode, self.current, error=str(exc))
        return UpdateStatus(True, self.mode, self.current, latest=release.version)

    async def install(self, before_launch: Callable[[], Awaitable[None]]) -> str:
        """Télécharge et vérifie l'installeur de la dernière version, appelle `before_launch`
        (mise en pause d'un nettoyage), puis lance l'installeur. Renvoie la version installée."""
        if not self.settings.update_check:
            raise UpdateRefused("Mises à jour désactivées (UPDATE_CHECK=false).")
        if self.mode != "installer":
            raise UpdateRefused(
                "Mise à jour automatique réservée à la version installée : télécharge la "
                "nouvelle version portable."
            )
        if self._installing:
            raise UpdateRefused("Mise à jour déjà en cours.")
        self._installing = True
        try:
            release = await self._latest()
            if not is_newer(release.version, self.current):
                raise UpdateRefused(f"IUC {self.current} est déjà à jour.")
            installer = await asyncio.to_thread(
                download, release, self.settings.updates_dir, self._opener
            )
            await before_launch()
            self._launcher(installer)
        except BaseException:
            self._installing = False
            raise
        logger.info("Mise à jour vers IUC %s : installeur lancé (%s).", release.version, installer)
        return release.version

    async def _latest(self) -> Release:
        first_check = self._release is None
        if self._release is None or time.monotonic() - self._checked_at > CHECK_INTERVAL:
            self._release = await asyncio.to_thread(fetch_latest, self._opener)
            self._checked_at = time.monotonic()
        if first_check:
            # Installeur de la mise à jour précédente, devenu inutile.
            await asyncio.to_thread(remove_downloads, self.settings.updates_dir)
        return self._release
