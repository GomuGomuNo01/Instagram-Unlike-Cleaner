"""Protection de l'API locale contre les autres pages ouvertes dans le navigateur.

Écouter sur 127.0.0.1 ne suffit pas : n'importe quel site ouvert dans un navigateur peut
envoyer des requêtes vers 127.0.0.1. D'où trois protections complémentaires :
- un jeton aléatoire, créé à chaque démarrage et exigé par toutes les routes de l'API ;
- un en-tête dédié pour le transmettre, ce qui oblige un autre site à passer par une
  vérification CORS préalable, refusée ;
- la vérification de l'en-tête Host (dans main.py), contre le « DNS rebinding ».
Le flux SSE accepte aussi le jeton en paramètre d'URL, car EventSource ne sait pas envoyer
d'en-tête ; ce flux est en lecture seule.
"""

import secrets
from typing import Annotated

from fastapi import HTTPException, Query, Request, Security, status
from fastapi.security import APIKeyHeader
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

TOKEN_HEADER = "X-IUC-Token"

_token_header = APIKeyHeader(
    name=TOKEN_HEADER,
    auto_error=False,
    description="Jeton affiché par `iuc serve` au démarrage de l'API.",
)


def new_token() -> str:
    return secrets.token_urlsafe(24)


def require_token(
    request: Request,
    header_token: Annotated[str | None, Security(_token_header)] = None,
    token: Annotated[str | None, Query(include_in_schema=False)] = None,
) -> None:
    expected: str = request.app.state.iuc.token
    provided = header_token or token or ""
    if not secrets.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Jeton manquant ou invalide (en-tête {TOKEN_HEADER}).",
        )


# En-têtes ajoutés à toutes les réponses : pas d'interprétation du type de contenu, pas
# d'adresse transmise aux autres sites, ressources réservées à l'interface d'IUC.
_COMMON_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class SecurityHeadersMiddleware:
    """Ajoute les en-têtes de sécurité, et interdit la mise en cache des réponses de l'API
    (elles contiennent des noms de comptes). Middleware ASGI pur : le flux SSE n'est pas
    retenu en mémoire."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_api = str(scope["path"]).startswith("/api/")

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in _COMMON_HEADERS.items():
                    headers.setdefault(name, value)
                if is_api:
                    headers.setdefault("Cache-Control", "no-store")
            await send(message)

        await self.app(scope, receive, send_with_headers)
