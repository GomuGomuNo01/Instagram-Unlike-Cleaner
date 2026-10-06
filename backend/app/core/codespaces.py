"""Exécution dans GitHub Codespaces : la vraie version d'IUC, dans la machine du testeur.

GitHub rend les ports de la machine accessibles par une adresse propre au Codespace,
https://<nom>-<port>.<domaine>, réservée par défaut à son propriétaire. L'API accepte
alors cet hôte en plus de 127.0.0.1 et localhost ; la fenêtre Chromium s'affiche dans un
bureau distant (noVNC, port 6080). Hors Codespaces, ces fonctions ne renvoient rien et rien
ne change.
"""

import os
import re
from collections.abc import Mapping

DESKTOP_PORT = 6080  # bureau distant de .devcontainer (fonctionnalité desktop-lite)

_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
_DOMAIN = re.compile(r"^[a-z0-9][a-z0-9.-]{0,99}$")


def forwarded_host(port: int, environ: Mapping[str, str] = os.environ) -> str | None:
    """Hôte public du port `port` dans le Codespace en cours, ou None hors Codespaces."""
    if environ.get("CODESPACES") != "true":
        return None
    name = environ.get("CODESPACE_NAME", "")
    domain = environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "")
    if not (_NAME.match(name) and _DOMAIN.match(domain)):
        return None
    return f"{name}-{port}.{domain}"


def desktop_url(environ: Mapping[str, str] = os.environ) -> str | None:
    """Adresse du bureau distant où s'affiche la fenêtre Chromium, ou None hors Codespaces."""
    host = forwarded_host(DESKTOP_PORT, environ)
    return f"https://{host}/vnc.html?autoconnect=true&resize=scale" if host else None
