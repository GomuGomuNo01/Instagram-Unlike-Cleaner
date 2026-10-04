"""Garde-fous de sécurité vérifiés à chaque lancement des tests."""

import re
from pathlib import Path

import app

# Tout accès à un champ de connexion serait une régression : le cahier des charges exige que
# le script ne lise ni ne remplisse jamais le formulaire de connexion d'Instagram.
LOGIN_FIELD_PATTERN = re.compile(
    r"password|passwd|mot.de.passe|name=.?username|autocomplete=.?current", re.IGNORECASE
)


def test_browser_code_never_touches_login_fields() -> None:
    browser_dir = Path(app.__file__).parent / "browser"

    offenders = [
        f"{path.name}:{number}: {line.strip()}"
        for path in sorted(browser_dir.glob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if LOGIN_FIELD_PATTERN.search(line)
    ]

    assert offenders == []
