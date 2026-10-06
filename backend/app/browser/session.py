"""Session navigateur : Chromium visible au profil persistant, connexion manuelle, navigation.

Le script ne lit ni ne remplit aucun champ de connexion : l'utilisateur se connecte lui-même
dans la fenêtre, et la connexion est détectée par la présence du cookie de session. Chromium
n'enregistre aucun identifiant et les diagnostics n'en contiennent jamais (voir
`app/core/privacy.py`).
"""

import asyncio
import logging
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import TracebackType
from typing import Self, cast
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.browser import locators
from app.browser.layout import layout_message, missing_on_likes_page
from app.browser.locators import PageKind
from app.core.privacy import SECRET_FIELD_SELECTOR, disable_credential_saving, redact_form_values

logger = logging.getLogger(__name__)

# Délai laissé à Instagram pour ouvrir une fenêtre par-dessus la page des likes, comme
# « Enregistrer vos informations de connexion ? » juste après une connexion.
DIALOG_SETTLE = 1.5
_URL_QUERY = re.compile(r"(https?://[^\s\"'?,]+)\?[^\s\"',]*")
# HTML de la première vignette de chaque type (Photo, Vidéo, Carrousel), pour les diagnostics.
_THUMBNAIL_SAMPLES_JS = """
() => {
  const labeled = '[role="button"][aria-label]';
  const samples = {};
  for (const element of document.querySelectorAll(labeled)) {
    if (element.parentElement && element.parentElement.closest(labeled)) continue;
    const kind = (element.getAttribute('aria-label') || '').split(/[\\s,]/)[0];
    if (kind && !(kind in samples)) samples[kind] = element.outerHTML;
  }
  return Object.values(samples);
}
"""


BROWSER_NAMES = {
    "chromium": "Chromium (playwright install chromium)",
    "chrome": "Google Chrome",
    "msedge": "Microsoft Edge",
}


class BrowserStartError(RuntimeError):
    """Le navigateur n'a pas pu être lancé (profil déjà utilisé, Chromium absent...)."""


class NavigationOutcome(StrEnum):
    OK = "ok"
    LOGIN_REQUIRED = "login_required"
    CHALLENGE = "challenge"
    CONSENT_REQUIRED = "consent_required"
    BLOCKING_DIALOG = "blocking_dialog"
    UNEXPECTED_PAGE = "unexpected_page"
    LAYOUT_CHANGED = "layout_changed"
    UNREACHABLE = "unreachable"


OUTCOME_MESSAGES: dict[NavigationOutcome, str] = {
    NavigationOutcome.OK: "Page des likes ouverte.",
    NavigationOutcome.LOGIN_REQUIRED: (
        "Instagram demande de se reconnecter. Connecte-toi dans la fenêtre puis relance."
    ),
    NavigationOutcome.CHALLENGE: (
        "Instagram affiche une vérification de sécurité. Termine-la toi-même dans la fenêtre, "
        "attends un peu, puis relance. Le script ne la contourne pas."
    ),
    NavigationOutcome.CONSENT_REQUIRED: (
        "Instagram affiche un écran de consentement (abonnement ou publicités). Fais ton choix "
        "toi-même dans la fenêtre, puis relance. Le script ne répond jamais à ta place."
    ),
    NavigationOutcome.BLOCKING_DIALOG: (
        "Une fenêtre d'Instagram recouvre la page des likes, par exemple « Enregistrer vos "
        "informations de connexion ? ». Ferme-la toi-même dans la fenêtre, puis relance. "
        "Le script n'y répond pas à ta place."
    ),
    NavigationOutcome.UNEXPECTED_PAGE: (
        "Instagram a affiché une autre page que celle des likes, par exemple après un clic "
        "dans la fenêtre. Ne clique pas dans la fenêtre pendant la vérification, puis relance."
    ),
    NavigationOutcome.LAYOUT_CHANGED: (
        "La page des likes n'a pas la structure attendue : l'interface d'Instagram a peut-être "
        "changé. Un diagnostic a été enregistré dans le dossier de données."
    ),
    NavigationOutcome.UNREACHABLE: "Instagram est injoignable. Vérifie ta connexion Internet.",
}

# Pages où l'utilisateur saisit ses identifiants ou un code : aucun diagnostic détaillé.
_PRIVATE_PAGES = frozenset({PageKind.LOGIN, PageKind.CHALLENGE})

# Pages sur lesquelles l'utilisateur doit agir lui-même : on s'arrête dès qu'on y arrive.
_STOP_PAGES: dict[PageKind, NavigationOutcome] = {
    PageKind.LOGIN: NavigationOutcome.LOGIN_REQUIRED,
    PageKind.CHALLENGE: NavigationOutcome.CHALLENGE,
    PageKind.CONSENT: NavigationOutcome.CONSENT_REQUIRED,
}


@dataclass(frozen=True)
class SessionStatus:
    browser_open: bool
    logged_in: bool
    account_id: str | None
    # Nature de la page affichée plutôt que son adresse, qui peut contenir le nom d'un compte.
    page: PageKind | None

    @property
    def challenge_required(self) -> bool:
        return self.page is PageKind.CHALLENGE

    @property
    def consent_required(self) -> bool:
        return self.page is PageKind.CONSENT


CLOSED_STATUS = SessionStatus(browser_open=False, logged_in=False, account_id=None, page=None)


class BrowserSession:
    """Pilote un Chromium au profil persistant. À utiliser avec `async with`."""

    def __init__(
        self,
        profile_dir: Path,
        *,
        headless: bool = False,
        extra_args: Sequence[str] = (),
        channels: Sequence[str] = ("chromium",),
    ) -> None:
        self._profile_dir = profile_dir
        self._headless = headless
        self._extra_args = list(extra_args)
        # Navigateurs essayés dans l'ordre : « chromium » (celui de Playwright), « chrome »,
        # « msedge ». Le premier qui s'ouvre est gardé.
        self._channels = list(channels)
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._closed_by_user = False
        self._layout_issue: str | None = None
        self._dialog_text: str | None = None

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def is_open(self) -> bool:
        return self._context is not None and not self._closed_by_user

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("Le navigateur n'est pas lancé")
        return self._context

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Le navigateur n'est pas lancé")
        return self._page

    @property
    def page_kind(self) -> PageKind:
        return locators.classify_path(urlparse(self.page.url).path)

    async def start(self) -> None:
        """Lance Chromium avec le profil persistant, sans ouvrir de page Instagram."""
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        disable_credential_saving(self._profile_dir)
        self._playwright = await async_playwright().start()
        failure: PlaywrightError | None = None
        for channel in self._channels:
            try:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    self._profile_dir,
                    channel=None if channel == "chromium" else channel,
                    headless=self._headless,
                    args=self._extra_args,
                    locale="fr-FR",
                    # Taille fixe : la mise en page d'Instagram, et donc les sélecteurs,
                    # change selon la largeur de la fenêtre.
                    viewport={"width": 1280, "height": 900},
                )
                break
            except PlaywrightError as exc:
                logger.info("Navigateur « %s » indisponible", channel)
                failure = exc
        if self._context is None:
            await self._playwright.stop()
            self._playwright = None
            browsers = ", ".join(BROWSER_NAMES.get(channel, channel) for channel in self._channels)
            raise BrowserStartError(
                "Impossible d'ouvrir le navigateur. Vérifie qu'aucune autre fenêtre IUC n'est "
                f"ouverte et qu'un de ces navigateurs est installé : {browsers}. "
                f"Détail : {failure}"
            ) from failure
        self._closed_by_user = False
        self._context.on("close", self._on_context_closed)
        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()
        logger.info("Navigateur lancé (profil : %s)", self._profile_dir)

    def _on_context_closed(self, _context: BrowserContext) -> None:
        self._closed_by_user = True
        logger.info("Fenêtre du navigateur fermée")

    async def close(self) -> None:
        if self._context is not None and not self._closed_by_user:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._context = None
        self._page = None
        self._playwright = None

    async def open_home(self) -> None:
        """Ouvre l'accueil d'Instagram, qui affiche le formulaire de connexion si besoin."""
        await self.page.goto(locators.HOME_URL, wait_until="domcontentloaded")

    async def status(self) -> SessionStatus:
        if not self.is_open:
            return CLOSED_STATUS
        cookies = await self.context.cookies(locators.BASE_URL)
        names = {cookie.get("name") for cookie in cookies}
        account_id = next(
            (c.get("value") for c in cookies if c.get("name") == locators.ACCOUNT_ID_COOKIE),
            None,
        )
        page = self.page_kind
        return SessionStatus(
            browser_open=True,
            logged_in=locators.SESSION_COOKIE in names and page is not PageKind.LOGIN,
            account_id=account_id,
            page=page,
        )

    async def wait_for_login(self, timeout: float, poll_interval: float = 2.0) -> SessionStatus:
        """Attend que l'utilisateur se connecte dans la fenêtre, ou que le délai expire."""
        deadline = time.monotonic() + timeout
        status = await self.status()
        while not status.logged_in and status.browser_open and time.monotonic() < deadline:
            await asyncio.sleep(poll_interval)
            status = await self.status()
        if status.logged_in:
            logger.info("Connexion détectée")
        return status

    @property
    def alert_message(self) -> str | None:
        """Texte de la fenêtre qui recouvrait la page des likes au dernier chargement, s'il
        signale une limite ou une erreur d'Instagram (« Réessayer plus tard »...)."""
        text = self._dialog_text
        return text if text and locators.ALERT_TEXT.search(text) else None

    def describe(self, outcome: NavigationOutcome) -> str:
        """Message pour l'utilisateur, avec l'élément manquant si l'interface a changé."""
        message = OUTCOME_MESSAGES[outcome]
        if outcome is NavigationOutcome.LAYOUT_CHANGED and self._layout_issue:
            message += f" Détail : {self._layout_issue}."
        return message

    async def interruption(self) -> NavigationOutcome | None:
        """Raison pour laquelle Instagram a interrompu le travail en cours, s'il l'a fait :
        déconnexion forcée, vérification de sécurité ou écran de consentement."""
        try:
            kind = self.page_kind
            if kind in _STOP_PAGES:
                return _STOP_PAGES[kind]
            if not (await self.status()).logged_in:
                return NavigationOutcome.LOGIN_REQUIRED
        except (PlaywrightError, RuntimeError):
            return NavigationOutcome.UNREACHABLE  # fenêtre fermée ou navigateur arrêté
        return None

    async def open_likes_page(self, timeout: float = 20.0) -> NavigationOutcome:
        """Ouvre la page des likes et vérifie que chaque élément attendu est présent."""
        self._layout_issue = None
        self._dialog_text = None
        try:
            await self.page.goto(locators.LIKES_URL, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            pass  # la page peut finir de se charger pendant la vérification ci-dessous
        except PlaywrightError as exc:
            logger.warning("Navigation vers la page des likes impossible : %s", exc)
            return NavigationOutcome.UNREACHABLE

        # Instagram peut rediriger côté serveur ou côté page : on surveille la page affichée
        # et l'apparition du repère jusqu'au délai, plutôt que de tester une seule fois.
        marker = locators.likes_page_marker(self.page)
        deadline = time.monotonic() + timeout
        while True:
            kind = self.page_kind
            if kind in _STOP_PAGES:
                outcome = _STOP_PAGES[kind]
                break
            if kind is PageKind.LIKES and await marker.is_visible():
                # Le repère peut être présent sous une fenêtre qui empêche tout clic.
                await asyncio.sleep(DIALOG_SETTLE)
                dialog = locators.blocking_dialog(self.page)
                if await dialog.is_visible():
                    self._dialog_text = " ".join((await dialog.inner_text()).split())
                    outcome = NavigationOutcome.BLOCKING_DIALOG
                elif missing := await missing_on_likes_page(self.page):
                    self._layout_issue = layout_message(missing)
                    outcome = NavigationOutcome.LAYOUT_CHANGED
                else:
                    outcome = NavigationOutcome.OK
                break
            if time.monotonic() >= deadline:
                if kind is PageKind.LIKES:
                    self._layout_issue = layout_message(
                        ["bouton « Trier et filtrer » et texte « Sélectionner »"]
                    )
                    outcome = NavigationOutcome.LAYOUT_CHANGED
                else:
                    outcome = NavigationOutcome.UNEXPECTED_PAGE
                break
            await asyncio.sleep(0.25)
        logger.info("Page des likes : %s (%s)", outcome, kind)
        return outcome

    async def save_diagnostic(self, directory: Path, label: str) -> Path:
        """Enregistre l'adresse, les liens, l'arbre d'accessibilité, le HTML d'une vignette
        de chaque type et une capture de la page.

        Sert à ajuster `locators.py`. Les fichiers restent dans le dossier de données local ;
        ils contiennent les noms des comptes aimés, à masquer avant de les partager.

        Identifiants : la valeur des champs de saisie est toujours masquée. Si un champ secret
        est affiché (connexion, fenêtre de ré-authentification), ou si la page est celle de
        connexion ou de vérification, seul le type de page est enregistré, sans capture ni
        contenu.
        """
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
        report = directory / f"{stem}.txt"
        kind = self.page_kind
        if kind in _PRIVATE_PAGES or await self.page.locator(SECRET_FIELD_SELECTOR).count():
            report.write_text(
                f"Page : {kind}\n\nDiagnostic réduit : un formulaire de connexion, un champ "
                "secret ou une vérification est affiché. Ni capture ni contenu de la page ne "
                "sont enregistrés, pour ne jamais conserver d'identifiant.\n",
                encoding="utf-8",
            )
            logger.info("Diagnostic réduit enregistré (%s) : %s", kind, report)
            return report
        hrefs = cast(
            list[str],
            await self.page.eval_on_selector_all(
                "a[href]", "links => links.map(link => link.getAttribute('href'))"
            ),
        )
        aria = redact_form_values(await self.page.locator("body").aria_snapshot())
        thumbnail_count = await locators.thumbnails(self.page).count()
        samples = cast(list[str], await self.page.evaluate(_THUMBNAIL_SAMPLES_JS))
        # Les paramètres des adresses d'images (signatures temporaires) sont retirés :
        # seul le nom du fichier sert d'identifiant.
        thumbnail_html = [redact_form_values(_URL_QUERY.sub(r"\1?…", sample)) for sample in samples]
        native_selects = await self.page.locator("select").count()
        # Adresse complète pour la page des likes seulement : ailleurs, elle peut contenir
        # le nom d'un compte.
        address = self.page.url if kind is PageKind.LIKES else str(kind)
        report.write_text(
            "\n".join(
                [
                    f"Adresse : {address}",
                    "",
                    f"== Liens ({len(hrefs)}) ==",
                    *hrefs,
                    "",
                    "== Arbre d'accessibilité ==",
                    aria,
                    "",
                    f"Listes déroulantes natives (select) : {native_selects}",
                    "",
                    f"== Vignettes ({thumbnail_count} chargées, HTML d'une vignette par type) ==",
                    *thumbnail_html,
                ]
            ),
            encoding="utf-8",
        )
        await self.page.screenshot(path=directory / f"{stem}.png", full_page=True)
        logger.info("Diagnostic enregistré : %s", report)
        return report
