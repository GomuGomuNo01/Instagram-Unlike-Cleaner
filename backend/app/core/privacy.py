"""Protection des identifiants Instagram : seul module autorisé à nommer un champ de mot de passe.

IUC ne lit ni ne remplit jamais le formulaire de connexion (le test de sécurité refuse toute
mention d'un tel champ dans `app/browser`). Ce module ne fait que s'en protéger :
- détecter qu'un champ secret est affiché, par simple comptage, sans jamais lire sa valeur ;
- masquer la valeur des champs de saisie dans les diagnostics, car l'arbre d'accessibilité de
  Playwright la reproduit en clair (« - textbox "Mot de passe": ... ») ;
- interdire à Chromium d'enregistrer un mot de passe ou de remplir un formulaire dans le
  profil, c'est-à-dire dans DATA_DIR.
"""

import json
import re
from pathlib import Path

# Champ secret : seule sa présence est testée, jamais son contenu.
SECRET_FIELD_SELECTOR = 'input[type="password"]'

# Ligne d'un champ de saisie dans l'arbre d'accessibilité : rôle, nom et attributs, puis valeur.
_FIELD_VALUE = re.compile(
    r"^(\s*- (?:textbox|searchbox|combobox|spinbutton)"
    r'(?: "(?:[^"\\]|\\.)*")?(?: \[[^\]]*\])*):.*$',
    re.MULTILINE,
)
_VALUE_ATTRIBUTE = re.compile(r'\svalue="[^"]*"')
MASK = "[valeur masquée]"


def redact_form_values(text: str) -> str:
    """Masque la valeur des champs de saisie dans un arbre d'accessibilité ou du HTML."""
    return _VALUE_ATTRIBUTE.sub(' value="…"', _FIELD_VALUE.sub(rf"\1: {MASK}", text))


def disable_credential_saving(profile_dir: Path) -> None:
    """Désactive dans le profil Chromium l'enregistrement des mots de passe et le remplissage
    automatique des formulaires, avant le lancement. Les autres préférences sont conservées."""
    preferences = profile_dir / "Default" / "Preferences"
    data: dict[str, object] = {}
    if preferences.is_file():
        try:
            loaded = json.loads(preferences.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = {}
        if isinstance(loaded, dict):
            data = loaded
    data["credentials_enable_service"] = False
    for section, keys in (
        ("profile", ("password_manager_enabled",)),
        ("autofill", ("profile_enabled", "credit_card_enabled")),
    ):
        values = data.get(section)
        if not isinstance(values, dict):
            values = {}
            data[section] = values
        for key in keys:
            values[key] = False
    preferences.parent.mkdir(parents=True, exist_ok=True)
    preferences.write_text(json.dumps(data), encoding="utf-8")
