"""Fausse version d'instagram.com pour tester l'automatisation sans aucun accès réseau."""

import time
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Route

from app.browser import locators

# Filet de sécurité : Chromium ne résout plus aucun nom de domaine. Une requête qui
# échapperait à l'interception échoue au lieu de partir sur Internet.
NO_NETWORK_ARGS = ["--host-resolver-rules=MAP * ~NOTFOUND"]


def html(body: str, script: str = "") -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'></head>"
        f"<body>{body}<script>{script}</script></body></html>"
    )


def thumbnail(index: int, total: int, kind: str = "Vidéo", author: str = "auteur_test") -> str:
    """Vignette fidèle à celles observées : un bouton sans lien, décrit par son libellé."""
    label = f"{kind}, {index} sur {total}, de @{author}, partagée le October 3, 2026"
    image = f"https://scontent.cdninstagram.com/v/t51.2885-15/{index}000_{index}_n.jpg"
    return (
        f"<div role='button' tabindex='0' aria-label='{label}' class='thumb'>"
        f"<img alt='' src='{image}?stp=dst-jpg&amp;oh=signature-secrete&amp;oe=ABC'></div>"
    )


def likes_grid(count: int) -> str:
    return "".join(thumbnail(index, count) for index in range(1, count + 1))


LIKES_PAGE_FR = html(
    "<h1>J’aime</h1><span>Du plus récent au plus ancien</span>"
    "<div role='button'>Trier et filtrer</div><span>Sélectionner</span>" + likes_grid(3)
)
LIKES_PAGE_EN = html("<h1>Likes</h1><span>Select</span>")


class FakeInstagram:
    """Sert des pages locales à la place d'instagram.com et bloque toute autre requête."""

    def __init__(self) -> None:
        self.offline = False
        self.requested_paths: list[str] = []
        self._pages: dict[str, tuple[int, str, dict[str, str]]] = {
            "/": (200, html("<h1>Accueil</h1>"), {}),
        }

    def page(self, path: str, body: str) -> None:
        self._pages[path] = (200, body, {})

    def redirect(self, path: str, location: str) -> None:
        """Redirection faite par la page elle-même.

        Une redirection HTTP (302) ne convient pas : Playwright n'intercepte pas la requête
        qui la suit, qui partirait sur le vrai instagram.com.
        """
        self._pages[path] = (200, html("", f"location.replace({location!r})"), {})

    def http_redirect(self, path: str, location: str) -> None:
        """Vraie redirection HTTP, réservée au test qui vérifie le blocage du réseau."""
        self._pages[path] = (302, "", {"location": location})

    async def install(self, context: BrowserContext) -> None:
        # Le dernier gestionnaire enregistré passe en premier : tout ce qui n'est pas
        # instagram.com tombe sur le blocage général.
        await context.route("**/*", lambda route: route.abort())
        await context.route(f"{locators.BASE_URL}/**", self._handle)

    async def _handle(self, route: Route) -> None:
        if self.offline:
            await route.abort("internetdisconnected")
            return
        path = urlparse(route.request.url).path
        self.requested_paths.append(path)
        status, body, headers = self._pages.get(path, (404, html("introuvable"), {}))
        await route.fulfill(
            status=status, headers=headers, body=body, content_type="text/html; charset=utf-8"
        )


async def log_in(context: BrowserContext, account_id: str = "1234567890") -> None:
    """Simule une connexion manuelle réussie : Instagram pose ses cookies de session."""
    expires = time.time() + 3600
    await context.add_cookies(
        [
            {
                "name": name,
                "value": value,
                "domain": ".instagram.com",
                "path": "/",
                "expires": expires,
                "secure": True,
            }
            for name, value in (
                (locators.SESSION_COOKIE, "faux-jeton"),
                (locators.ACCOUNT_ID_COOKIE, account_id),
            )
        ]
    )
