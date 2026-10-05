"""Tests de l'exploration sur une fausse page des likes interactive, sans aucun accès réseau."""

from pathlib import Path

import pytest

from app.browser import locators, probe
from app.browser.session import BrowserSession, NavigationOutcome
from tests.fake_instagram import LIKES_PAGE_CHANGED, FakeInstagram, html, likes_grid, log_in

pytestmark = [pytest.mark.anyio, pytest.mark.browser]

# Le panneau de filtres et le mode sélection imitent la page réelle. Les actions qui
# modifieraient le compte appellent une adresse témoin, que le test surveille.
INTERACTIVE_LIKES_PAGE = html(
    "<span>Du plus récent au plus ancien</span>"
    "<div role='button' id='filters'>Trier et filtrer</div>"
    "<span id='select'>Sélectionner</span>"
    "<div id='grid'>" + likes_grid(3) + "</div>",
    """
    let selecting = false;
    document.getElementById('filters').onclick = () => {
      document.body.insertAdjacentHTML('beforeend',
        "<div role='dialog'><h2>Trier et filtrer</h2>" +
        "<label><input type='radio' name='sort' checked>Du plus récent au plus ancien</label>" +
        "<button id='apply'>Appliquer</button></div>");
      document.getElementById('apply').onclick = () => fetch('/__filtre_applique__');
    };
    document.getElementById('select').onclick = () => {
      selecting = true;
      document.body.insertAdjacentHTML('beforeend',
        "<span id='counter'>0 sélectionné</span><button id='unlike'>Ne plus aimer</button>");
      document.getElementById('unlike').onclick = () => fetch('/__unlike__');
      document.querySelectorAll('.thumb').forEach(t => t.setAttribute('aria-pressed', 'false'));
    };
    document.querySelectorAll('.thumb').forEach(t => t.onclick = () => {
      if (!selecting) { location.href = '/p/ouvert/'; return; }
      t.setAttribute('aria-pressed', 'true');
      document.getElementById('counter').textContent = '1 sélectionné';
    });
    """,
)

FORBIDDEN_PATHS = {"/__unlike__", "/__filtre_applique__"}


@pytest.fixture(autouse=True)
def fast_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe, "SETTLE_DELAY", 0.2)
    monkeypatch.setattr(probe, "CLICK_TIMEOUT_MS", 1_000)


def labels(reports: list[Path]) -> list[str]:
    return [report.stem.split("-", 2)[2] for report in reports]


async def open_likes(
    session: BrowserSession,
    fake_instagram: FakeInstagram,
    body: str,
    expected: NavigationOutcome = NavigationOutcome.OK,
) -> None:
    fake_instagram.page(locators.LIKES_PATH, body)
    await log_in(session.context)
    assert await session.open_likes_page(timeout=5) is expected


async def test_probe_explores_filters_and_selection_without_unliking(
    session: BrowserSession, fake_instagram: FakeInstagram, tmp_path: Path
) -> None:
    await open_likes(session, fake_instagram, INTERACTIVE_LIKES_PAGE)

    reports = await probe.run_probe(session, tmp_path / "diagnostics")

    assert labels(reports) == ["likes", "filtres", "selection", "selection-1-element"]
    contents = {
        label: report.read_text(encoding="utf-8")
        for label, report in zip(labels(reports), reports, strict=True)
    }
    assert "Appliquer" in contents["filtres"]
    assert "Ne plus aimer" in contents["selection"]
    assert "1 sélectionné" in contents["selection-1-element"]
    assert FORBIDDEN_PATHS.isdisjoint(fake_instagram.requested_paths)


async def test_probe_leaves_the_page_reloaded_and_unselected(
    session: BrowserSession, fake_instagram: FakeInstagram, tmp_path: Path
) -> None:
    await open_likes(session, fake_instagram, INTERACTIVE_LIKES_PAGE)

    await probe.run_probe(session, tmp_path / "diagnostics")

    assert not await session.page.get_by_text("Ne plus aimer").is_visible()
    assert not await session.page.get_by_role("dialog").is_visible()
    # Ouverture initiale, puis un rechargement après chaque étape.
    assert fake_instagram.requested_paths.count(locators.LIKES_PATH) == 3


async def test_probe_skips_missing_elements(
    session: BrowserSession, fake_instagram: FakeInstagram, tmp_path: Path
) -> None:
    # Interface modifiée, sans bouton de filtres ni vignettes : l'exploration a lieu quand
    # même, et les étapes concernées sont sautées.
    await open_likes(session, fake_instagram, LIKES_PAGE_CHANGED, NavigationOutcome.LAYOUT_CHANGED)

    reports = await probe.run_probe(session, tmp_path / "diagnostics")

    assert labels(reports) == ["likes", "selection"]
