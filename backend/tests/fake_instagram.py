"""Fausse version d'instagram.com pour tester l'automatisation sans aucun accès réseau."""

import json
import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
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


@dataclass(frozen=True)
class FakeLike:
    key: str  # nom du fichier image, sans extension
    kind: str  # début du libellé : « Photo », « Vidéo » ou « Carrousel avec N éléments »
    author: str
    published: str  # date de publication, en anglais comme sur Instagram
    liked: str  # date du like (AAAA-MM-JJ), utilisée par le faux filtre de dates


def make_likes(count: int, *, latest: date = date(2026, 9, 30)) -> list[FakeLike]:
    """Likes du plus récent au plus ancien, un tous les 5 jours, types et auteurs alternés."""
    kinds = ("Vidéo", "Photo", "Carrousel avec 3 éléments")
    return [
        FakeLike(
            key=f"{900000 + index}_{18000000000000000 + index}_{index}_n",
            kind=kinds[index % 3],
            author=("auteur_a", "auteur.b", "auteur_c", "auteur_d")[index % 4],
            published="October 3, 2026",
            liked=(latest - timedelta(days=5 * index)).isoformat(),
        )
        for index in range(count)
    ]


# Fausse page des likes, fidèle aux diagnostics d'octobre 2026 : paquets de 18 vignettes dont
# la numérotation repart à 1, défilement dans un panneau interne, indicateur « Chargement... »,
# et panneau « Trier et filtrer » avec tri et listes déroulantes de dates. Appliquer un
# filtre appelle /__filtre__/<début>/<fin>/<tri>, que les tests peuvent surveiller.
_LIKES_PAGE_SCRIPT = """
const ALL = __DATA__;
const BATCH = 18;
const MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
  'septembre', 'octobre', 'novembre', 'décembre'];
const dates = ALL.map(item => item.liked).sort();
const DEFAULT_START = dates[0] || '2026-01-01';
const DEFAULT_END = dates[dates.length - 1] || '2026-01-01';
let state = {sort: 'newest_first', start: DEFAULT_START, end: DEFAULT_END};
let visible = [];
let shown = 0;
const grid = document.getElementById('grid');
const observer = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (entry.isIntersecting) { observer.unobserve(entry.target); setTimeout(loadBatch, 150); }
  }
}, {root: grid});

function filtered() {
  const items = ALL.filter(i => i.liked >= state.start && i.liked <= state.end);
  items.sort((a, b) => b.liked.localeCompare(a.liked));
  return state.sort === 'oldest_first' ? items.reverse() : items;
}
function thumbnail(item, index, total) {
  const element = document.createElement('div');
  element.setAttribute('role', 'button');
  element.setAttribute('tabindex', '0');
  element.setAttribute('aria-label',
    `${item.kind}, ${index} sur ${total}, de @${item.author}, partagée le ${item.published}`);
  element.style.cssText = 'display:inline-block;width:120px;height:160px;margin:2px;';
  const icon = item.kind.startsWith('Carrousel')
    ? '<div style="mask-image: url(&quot;https://i.instagram.com/static/images/bloks/icons/'
      + 'generated/carousel__filled__32-4x.png&quot;);"></div>'
    : '';
  element.innerHTML = '<img alt="" src="https://instagram.fcdg3-1.fna.fbcdn.net/v/t51.82787-15/'
    + item.key + '.jpg?stp=dst-jpg&oh=signature&oe=ABC">' + icon;
  return element;
}
function loadBatch() {
  const progress = document.getElementById('progress');
  if (progress) progress.remove();
  const batch = visible.slice(shown, shown + BATCH);
  batch.forEach((item, i) => grid.appendChild(thumbnail(item, i + 1, batch.length)));
  shown += batch.length;
  if (shown < visible.length) {
    const bar = document.createElement('div');
    bar.id = 'progress';
    bar.setAttribute('role', 'progressbar');
    bar.textContent = 'Chargement...';
    bar.style.cssText = 'height:40px;';
    grid.appendChild(bar);
    observer.observe(bar);
  }
}
function render() { grid.innerHTML = ''; visible = filtered(); shown = 0; loadBatch(); }

function dateSelects(prefix, value) {
  const [year, month, day] = value.split('-').map(Number);
  const options = (values, labels, selected) => values.map((v, i) =>
    `<option value="${v}"${v === selected ? ' selected' : ''}>${labels[i]}</option>`).join('');
  const days = Array.from({length: 31}, (_, i) => i + 1);
  const years = Array.from({length: 7}, (_, i) => 2026 - i);
  return `<select id="${prefix}-month" aria-label="Mois :">`
      + options(MONTHS.map((_, i) => i + 1), MONTHS, month) + '</select>'
    + `<select id="${prefix}-day" aria-label="Jour :">` + options(days, days, day) + '</select>'
    + `<select id="${prefix}-year" aria-label="Année :">` + options(years, years, year)
    + '</select>';
}
function readDate(prefix) {
  const pad = n => String(n).padStart(2, '0');
  const value = id => Number(document.getElementById(`${prefix}-${id}`).value);
  return `${value('year')}-${pad(value('month'))}-${pad(value('day'))}`;
}
document.getElementById('filters').onclick = () => {
  const dialog = document.createElement('div');
  dialog.setAttribute('role', 'dialog');
  dialog.innerHTML = '<div>Trier et filtrer</div><div>Trier par</div>'
    + '<div role="button" data-sort="newest_first">Du plus récent au plus ancien</div>'
    + '<div role="button" data-sort="oldest_first">Du plus ancien au plus récent</div>'
    + '<div>Date de début</div>' + dateSelects('start', state.start)
    + '<div>Date de fin</div>' + dateSelects('end', state.end)
    + '<button id="apply" disabled>Appliquer</button>';
  document.body.appendChild(dialog);
  let sort = state.sort;
  const apply = document.getElementById('apply');
  const refresh = () => {
    apply.disabled = sort === state.sort && readDate('start') === state.start
      && readDate('end') === state.end;
  };
  dialog.querySelectorAll('[data-sort]').forEach(button => button.onclick = () => {
    sort = button.dataset.sort; refresh();
  });
  dialog.querySelectorAll('select').forEach(select => select.onchange = refresh);
  apply.onclick = () => {
    state = {sort, start: readDate('start'), end: readDate('end')};
    fetch(`/__filtre__/${state.start}/${state.end}/${state.sort}`);
    document.getElementById('sort-label').textContent = sort === 'newest_first'
      ? 'Du plus récent au plus ancien' : 'Du plus ancien au plus récent';
    dialog.remove();
    setTimeout(render, 100);
  };
};
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') document.querySelectorAll('[role="dialog"]').forEach(d => d.remove());
});
if (__BLOCKING_AFTER_MS__ >= 0) {
  setTimeout(() => document.body.insertAdjacentHTML('beforeend',
    '<div role="dialog">Enregistrer vos informations de connexion ?'
    + '<button>Enregistrer les informations</button><button>Plus tard</button></div>'),
    __BLOCKING_AFTER_MS__);
}
render();
"""


def interactive_likes_page(likes: list[FakeLike], *, blocking_dialog_after_ms: int = -1) -> str:
    """Page des likes interactive. `blocking_dialog_after_ms` ouvre, après ce délai, la
    fenêtre « Enregistrer vos informations de connexion ? » par-dessus la page."""
    script = _LIKES_PAGE_SCRIPT.replace(
        "__DATA__", json.dumps([asdict(like) for like in likes], ensure_ascii=False)
    ).replace("__BLOCKING_AFTER_MS__", str(blocking_dialog_after_ms))
    return html(
        "<span id='sort-label'>Du plus récent au plus ancien</span>"
        "<div role='button' id='filters'>Trier et filtrer</div><span>Sélectionner</span>"
        "<div id='grid' style='width:400px;height:400px;overflow-y:auto;'></div>",
        script,
    )


def selection_mode_page(likes: list[FakeLike], checked: int) -> str:
    """Grille en mode sélection, statique : chaque vignette contient un second bouton au même
    libellé et une case, comme observé. La vignette n° `checked` est cochée."""
    thumbnails = []
    for index, like in enumerate(likes):
        label = (
            f"{like.kind}, {index + 1} sur {len(likes)}, de @{like.author}, "
            f"partagée le {like.published}"
        )
        icon = "circle-check__filled__24" if index == checked else "circle__outline__24"
        thumbnails.append(
            f"<div role='button' tabindex='0' aria-label='{label}'>"
            f"<div role='button' aria-label='{label}'><img alt='' "
            f"src='https://instagram.fcdg3-1.fna.fbcdn.net/v/t51.82787-15/{like.key}.jpg?oe=1'>"
            "</div><div role='button' aria-label='Activer la case à cocher'>"
            "<div style='mask-image: url(&quot;"
            f"https://i.instagram.com/static/images/bloks/icons/generated/{icon}-4x.png"
            "&quot;);'></div></div></div>"
        )
    return html(
        "<div role='button'>Trier et filtrer</div><span>Annuler</span>" + "".join(thumbnails)
    )


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
