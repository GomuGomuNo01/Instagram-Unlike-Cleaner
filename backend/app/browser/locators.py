"""Adresses, cookies et sélecteurs Instagram, centralisés pour absorber les changements d'interface.

Tout ce qui dépend du HTML d'Instagram doit passer par ce module. Les textes sont donnés en
français et en anglais, car la langue de l'interface suit le réglage du compte.

Les valeurs marquées « à confirmer » viennent d'observations de l'interface web et doivent
être vérifiées avec `iuc login --snapshot` sur un compte de test.

Le module s'appelle `locators` et non `selectors` pour ne pas masquer le module standard.
"""

import re

from playwright.async_api import Locator, Page

BASE_URL = "https://www.instagram.com"
HOME_URL = f"{BASE_URL}/"
LIKES_URL = f"{BASE_URL}/your_activity/interactions/likes/"  # à confirmer

# On ne teste que la présence de ces cookies : leur valeur n'est jamais lue ni journalisée,
# sauf l'identifiant numérique du compte.
SESSION_COOKIE = "sessionid"
ACCOUNT_ID_COOKIE = "ds_user_id"

LOGIN_PATH = re.compile(r"^/accounts/login(/|$)")
CHALLENGE_PATH = re.compile(
    r"^/(challenge|checkpoint|accounts/suspended|accounts/disabled)(/|$)"  # à confirmer
)

_SELECT_TEXT = re.compile(r"^\s*(Sélectionner|Select)\s*$")  # à confirmer
_SORT_AND_FILTER_TEXT = re.compile(r"^\s*(Trier et filtrer|Sort (&|and) filter)\s*$")  # à confirmer


def likes_page_marker(page: Page) -> Locator:
    """Élément qui prouve que la page des likes est chargée et a la structure attendue."""
    return page.get_by_text(_SELECT_TEXT).or_(page.get_by_text(_SORT_AND_FILTER_TEXT)).first
