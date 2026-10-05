"""Sécurité et robustesse (cahier des charges, section 7), vérifiées à chaque lancement des tests.

Le code doit prouver qu'il ne manipule jamais de mot de passe et qu'il s'arrête au moindre
signal d'Instagram. Ce fichier regroupe les preuves par exigence ; les arrêts sur alerte, la
cadence et la reprise sont testés sur la fausse page des likes dans test_cleanup.py.
"""

import ast
import json
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from typer.testing import CliRunner

import app
from app import cli
from app.browser import locators
from app.browser.session import BrowserSession, NavigationOutcome
from app.core.config import Settings
from app.core.db import init_db, make_engine
from app.core.logs import LOG_FILE_NAME, setup_logging
from app.core.privacy import MASK, redact_form_values
from app.main import create_app
from app.models.schemas import CleanupFilters
from app.services.cleanup import StopReason
from app.services.preview import run_preview
from tests.fake_instagram import (
    LIKES_PAGE_FR,
    NO_NETWORK_ARGS,
    FakeInstagram,
    html,
    log_in,
    make_likes,
)

APP_DIR = Path(app.__file__).parent
ROOT = APP_DIR.parents[1]


def python_files(directory: Path) -> Iterator[tuple[Path, ast.Module]]:
    for path in sorted(directory.rglob("*.py")):
        yield path, ast.parse(path.read_text(encoding="utf-8"))


# --- Identifiants : aucun champ de connexion lu ni rempli, aucun mot de passe conservé ------

# Tout accès à un champ de connexion serait une régression : le cahier des charges exige que
# le script ne lise ni ne remplisse jamais le formulaire de connexion d'Instagram. Seul
# app/core/privacy.py nomme un tel champ, et uniquement pour s'en protéger.
LOGIN_FIELD_PATTERN = re.compile(
    r"password|passwd|mot.de.passe|name=.?username|autocomplete=.?current", re.IGNORECASE
)
# Méthodes Playwright qui saisissent du texte ou lisent la valeur d'un champ.
TYPING_OR_READING = {
    "fill",
    "type",
    "press_sequentially",
    "insert_text",
    "input_value",
    "set_input_files",
    "select_text",
}
# Lecture de la valeur d'un champ depuis un script exécuté dans la page.
JS_VALUE_READ = re.compile(r"\.value\b")


def test_browser_code_never_touches_login_fields() -> None:
    browser_dir = APP_DIR / "browser"

    offenders = [
        f"{path.name}:{number}: {line.strip()}"
        for path in sorted(browser_dir.glob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if LOGIN_FIELD_PATTERN.search(line)
    ]

    assert offenders == []


def test_app_never_types_into_or_reads_a_field() -> None:
    offenders = []
    for path, tree in python_files(APP_DIR):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                name = node.func.attr
                first = node.args[0] if node.args else None
                literal = first.value if isinstance(first, ast.Constant) else None
                if (
                    name in TYPING_OR_READING
                    or (name == "get_attribute" and literal == "value")
                    # Seule touche autorisée : Échap, pour refermer le panneau des filtres.
                    or (name == "press" and literal != "Escape")
                ):
                    offenders.append(f"{path.name}:{node.lineno}: .{name}()")
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and "=>" in node.value
                and JS_VALUE_READ.search(node.value)
            ):
                offenders.append(f"{path.name}:{node.lineno}: script lisant .value")

    assert offenders == []


def test_diagnostics_mask_every_field_value() -> None:
    snapshot = "\n".join(
        [
            '- textbox "Nom d\'utilisateur": moncompte',
            '- textbox "Mot de passe" [disabled]: Secret!42',
            "- searchbox: recherche",
            '  - combobox "Mois :": octobre',
            '- button "Se connecter"',
            '<input type="text" value="defaut">',
        ]
    )

    redacted = redact_form_values(snapshot)

    assert "moncompte" not in redacted and "Secret!42" not in redacted
    assert "recherche" not in redacted and "octobre" not in redacted
    assert "defaut" not in redacted
    assert redacted.count(MASK) == 4
    assert '- button "Se connecter"' in redacted


LOGIN_FORM = html(
    "<form><label>Nom d'utilisateur <input name='username'></label>"
    "<label>Mot de passe <input type='password' name='password'></label>"
    "<button type='button'>Se connecter</button></form>"
)
# Fenêtre de ré-authentification par-dessus la page des likes.
REAUTH_LIKES_PAGE = LIKES_PAGE_FR.replace(
    "</body>",
    "<div role='dialog'>Confirme ton identité <label>Mot de passe "
    "<input type='password'></label></div></body>",
)
SECRET = "Canari-Secret-8641!"
USERNAME = "identifiant.canari"


def files_written(settings: Settings) -> dict[Path, bytes]:
    """Tout ce qu'IUC a écrit dans DATA_DIR, hors profil du navigateur (géré par Chromium)."""
    return {
        path: path.read_bytes()
        for path in settings.data_dir.rglob("*")
        if path.is_file() and settings.browser_profile_dir not in path.parents
    }


def assert_never_written(settings: Settings, *secrets: str) -> None:
    for path, content in files_written(settings).items():
        for secret in secrets:
            for encoding in ("utf-8", "utf-16-le"):
                assert secret.encode(encoding) not in content, f"{secret!r} trouvé dans {path}"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    settings = Settings(_env_file=None, data_dir=tmp_path / "data", log_level="DEBUG")
    settings.ensure_dirs()
    setup_logging(settings)
    return settings


@pytest.mark.anyio
@pytest.mark.browser
async def test_typed_credentials_never_leave_the_window(
    session: BrowserSession, fake_instagram: FakeInstagram, settings: Settings
) -> None:
    fake_instagram.page("/accounts/login/", LOGIN_FORM)
    fake_instagram.redirect(locators.LIKES_PATH, "/accounts/login/")
    page = session.page
    await page.goto(f"{locators.BASE_URL}/accounts/login/")
    # L'utilisateur tape ses identifiants dans la fenêtre (ici, le test joue son rôle).
    await page.get_by_label("Nom d'utilisateur").press_sequentially(USERNAME)
    await page.get_by_label("Mot de passe").press_sequentially(SECRET)

    assert not (await session.status()).logged_in
    assert not (await session.wait_for_login(timeout=0.3, poll_interval=0.1)).logged_in
    report = await session.save_diagnostic(settings.diagnostics_dir, "connexion")
    assert await session.open_likes_page(timeout=3) is NavigationOutcome.LOGIN_REQUIRED

    assert "Diagnostic réduit" in report.read_text(encoding="utf-8")
    assert not list(settings.diagnostics_dir.glob("*.png"))  # aucune capture de l'écran
    assert (settings.logs_dir / LOG_FILE_NAME).stat().st_size > 0
    assert_never_written(settings, SECRET, USERNAME)


@pytest.mark.anyio
@pytest.mark.browser
async def test_reauthentication_window_is_never_recorded(
    session: BrowserSession, fake_instagram: FakeInstagram, settings: Settings
) -> None:
    fake_instagram.page(locators.LIKES_PATH, REAUTH_LIKES_PAGE)
    await log_in(session.context)
    await session.page.goto(locators.LIKES_URL)
    await session.page.get_by_label("Mot de passe").press_sequentially(SECRET)

    report = await session.save_diagnostic(settings.diagnostics_dir, "likes")

    assert "Diagnostic réduit" in report.read_text(encoding="utf-8")
    assert not list(settings.diagnostics_dir.glob("*.png"))
    assert_never_written(settings, SECRET)


@pytest.mark.anyio
@pytest.mark.browser
async def test_collected_data_never_contains_session_secrets(
    session: BrowserSession, fake_instagram: FakeInstagram, settings: Settings
) -> None:
    fake_instagram.serve_likes(make_likes(5))
    await log_in(session.context)
    assert await session.open_likes_page(timeout=5) is NavigationOutcome.OK
    engine = make_engine(settings.db_path)
    init_db(engine)
    try:
        await run_preview(session, engine, CleanupFilters(), account_id="1234567890")
        await session.save_diagnostic(settings.diagnostics_dir, "likes")
    finally:
        engine.dispose()

    # Valeur du cookie de session posé par la fausse connexion (tests/fake_instagram.py).
    assert_never_written(settings, "faux-jeton")


@pytest.mark.anyio
@pytest.mark.browser
async def test_chromium_never_offers_to_save_credentials(tmp_path: Path) -> None:
    profile = tmp_path / "profil"
    (profile / "Default").mkdir(parents=True)
    preferences = profile / "Default" / "Preferences"
    preferences.write_text(json.dumps({"intl": {"accept_languages": "fr"}}), encoding="utf-8")

    async with BrowserSession(profile, headless=True, extra_args=NO_NETWORK_ARGS):
        pass

    saved = json.loads(preferences.read_text(encoding="utf-8"))
    assert saved["credentials_enable_service"] is False
    assert saved["autofill"]["profile_enabled"] is False
    assert saved["intl"]["accept_languages"] == "fr"  # les autres préférences sont gardées


# --- Données locales : tout dans DATA_DIR, aucun appel vers un serveur tiers --------------

# Bibliothèques capables de contacter un serveur : seul Chromium, piloté par Playwright,
# parle à Instagram. L'API ne fait qu'écouter sur 127.0.0.1 (uvicorn).
NETWORK_MODULES = (
    "requests",
    "httpx",
    "urllib.request",
    "urllib3",
    "http.client",
    "aiohttp",
    "socket",
    "ftplib",
    "smtplib",
    "websockets",
)


def test_backend_never_opens_a_network_connection_itself() -> None:
    offenders = []
    for path, tree in python_files(APP_DIR):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module, *(f"{node.module}.{a.name}" for a in node.names)]
            else:
                continue
            offenders += [
                f"{path.name}:{node.lineno}: {name}"
                for name in names
                if name.startswith(NETWORK_MODULES)
            ]

    assert offenders == []


def test_every_local_file_lives_in_data_dir(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, data_dir=tmp_path / "donnees")

    for path in (
        settings.db_path,
        settings.browser_profile_dir,
        settings.reports_dir,
        settings.logs_dir,
        settings.diagnostics_dir,
    ):
        assert settings.data_dir in path.parents


def make_dist(root: Path) -> Path:
    dist = root / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><html><head></head><body></body></html>", encoding="utf-8"
    )
    return dist


async def http_client(app_: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app_), base_url="http://127.0.0.1")


@pytest.mark.anyio
async def test_interface_may_only_talk_to_the_local_api(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None, data_dir=tmp_path / "data", frontend_dist=make_dist(tmp_path)
    )
    api = create_app(settings, token="jeton")
    async with await http_client(api) as http:
        policy = (await http.get("/")).headers["content-security-policy"]
    api.state.iuc.engine.dispose()

    directives = dict(item.strip().split(" ", 1) for item in policy.split(";"))
    for directive in ("default-src", "script-src", "style-src", "font-src", "connect-src"):
        assert directives[directive] == "'self'"
    assert directives["frame-ancestors"] == "'none'"
    assert "unsafe" not in policy and "http" not in policy


@pytest.mark.anyio
@pytest.mark.parametrize("enabled", [False, True], ids=["par-defaut", "API_DOCS"])
async def test_api_docs_page_using_a_cdn_is_opt_in(tmp_path: Path, enabled: bool) -> None:
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        frontend_dist=make_dist(tmp_path),
        api_docs=enabled,
    )
    api = create_app(settings, token="jeton")
    async with await http_client(api) as http:
        docs = await http.get("/docs")
        schema = await http.get("/openapi.json")
    api.state.iuc.engine.dispose()

    assert ("swagger-ui" in docs.text) is enabled
    assert schema.status_code == 200


# --- API locale : 127.0.0.1 uniquement, en-têtes de sécurité --------------------------------


def test_serve_listens_on_localhost_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    listened: dict[str, object] = {}

    class FakeServer:
        def __init__(self, config: uvicorn.Config) -> None:
            listened.update(host=config.host, port=config.port)
            self.started = True

        async def serve(self) -> None:
            return None

    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["serve", "--no-open", "--port", "8799"])

    assert result.exit_code == 0, result.output
    assert listened == {"host": "127.0.0.1", "port": 8799}
    assert "--host" not in runner.invoke(cli.app, ["serve", "--help"]).output


@pytest.mark.anyio
async def test_every_response_carries_security_headers(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None, data_dir=tmp_path / "data", frontend_dist=make_dist(tmp_path)
    )
    api = create_app(settings, token="jeton")
    async with await http_client(api) as http:
        allowed = await http.get("/api/session/status", headers={"X-IUC-Token": "jeton"})
        refused = await http.get("/api/session/status")
        page = await http.get("/")
    api.state.iuc.engine.dispose()

    assert (allowed.status_code, refused.status_code) == (200, 401)
    for response in (allowed, refused, page):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cross-origin-resource-policy"] == "same-origin"
    # Les réponses de l'API contiennent des noms de comptes : jamais mises en cache.
    assert allowed.headers["cache-control"] == "no-store"


# --- Alertes : chaque arrêt a sa marche à suivre dans l'interface ------------------------


def test_every_stop_reason_has_advice_in_the_interface() -> None:
    texts = (ROOT / "frontend" / "src" / "i18n" / "fr.ts").read_text(encoding="utf-8")
    advice = texts.split("export const stopAdvice", 1)[1]

    missing = [
        reason.value for reason in StopReason if not re.search(rf"\b{reason.value}:", advice)
    ]

    assert missing == []


# --- Dépendances : versions figées -------------------------------------------------------


def test_dependencies_are_pinned() -> None:
    constraints = {
        name.lower().replace("_", "-"): version
        for line in (ROOT / "constraints.txt").read_text(encoding="utf-8").splitlines()
        if "==" in line and not line.startswith("#")
        for name, version in [line.split("==", 1)]
    }
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.findall(r'^\s+"([A-Za-z0-9_.-]+)(?:\[[a-z,]+\])?>=', pyproject, re.MULTILINE)

    assert declared, "aucune dépendance lue dans pyproject.toml"
    unpinned = [name for name in declared if name.lower().replace("_", "-") not in constraints]
    assert unpinned == []
    assert (ROOT / "frontend" / "package-lock.json").is_file()
