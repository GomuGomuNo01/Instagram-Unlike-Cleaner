"""Service de l'interface compilée (frontend/dist) par l'API, avec le jeton injecté.

La page reçoit le jeton dans une balise <meta name="iuc-token"> : un autre site peut
demander cette page, mais pas en lire le contenu (CORS), ni se faire passer pour
127.0.0.1 (contrôle de l'hôte). Elle ne peut pas non plus être affichée dans un cadre d'un
autre site (protection contre le « clickjacking »).

Sa politique de sécurité du contenu (CSP) n'autorise que l'API locale elle-même : scripts,
styles, polices, images et requêtes. Le navigateur refuse donc tout appel de l'interface
vers un serveur tiers, et tout script injecté dans la page.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

TOKEN_META = "iuc-token"
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
_PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}
# Page d'aide (interface non compilée) : quelques styles écrits dans la page elle-même.
_FALLBACK_HEADERS = {
    **_PAGE_HEADERS,
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
    "frame-ancestors 'none'",
}
_NOT_BUILT = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>IUC</title></head>
<body style="font-family: system-ui; max-width: 40rem; margin: 3rem auto; line-height: 1.5">
<h1>Interface non compilée</h1>
<p>L'API fonctionne, mais l'interface n'a pas encore été compilée. Dans le dossier
<code>frontend</code>, lance <code>npm install</code> puis <code>npm run build</code>,
et relance <code>iuc serve</code>.</p>
<p>Le schéma de l'API s'exporte avec <code>iuc openapi schema.json</code>.</p>
</body></html>"""


def mount_frontend(app: FastAPI, dist: Path, token: str) -> None:
    """Sert les fichiers de l'interface et renvoie index.html pour ses routes. À appeler
    après l'ajout des routes de l'API, qui restent prioritaires."""
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> Response:
        if path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Route inconnue.")
        root = dist.resolve()
        file = (dist / path).resolve()
        if path and file.is_file() and root in file.parents:
            return FileResponse(file)  # favicon, icônes...
        index = dist / "index.html"
        if not index.is_file():
            return HTMLResponse(_NOT_BUILT, status.HTTP_503_SERVICE_UNAVAILABLE, _FALLBACK_HEADERS)
        page = index.read_text(encoding="utf-8").replace(
            "</head>", f'<meta name="{TOKEN_META}" content="{token}" />\n</head>', 1
        )
        return HTMLResponse(page, headers=_PAGE_HEADERS)
