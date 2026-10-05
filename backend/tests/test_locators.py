import pytest

from app.browser import locators
from app.browser.locators import PageKind, classify_path


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/", PageKind.HOME),
        ("", PageKind.HOME),
        ("/your_activity/interactions/likes/", PageKind.LIKES),
        ("/your_activity/interactions/likes", PageKind.LIKES),
        ("/accounts/login/", PageKind.LOGIN),
        ("/accounts/login/two_factor", PageKind.LOGIN),
        ("/challenge/action/", PageKind.CHALLENGE),
        ("/accounts/suspended/", PageKind.CHALLENGE),
        ("/consent/", PageKind.CONSENT),
        ("/un_compte/", PageKind.OTHER),
        ("/your_activity/interactions/comments", PageKind.OTHER),
    ],
)
def test_classify_path(path: str, expected: PageKind) -> None:
    assert classify_path(path) is expected


@pytest.mark.parametrize(
    "label",
    [
        # Formes observées sur l'interface française (auteurs remplacés).
        "Vidéo, 2 sur 18, de @auteur.un, partagée le October 3, 2026",
        "Photo, 3 sur 18, de @auteur_deux, partagée le October 2, 2026",
        "Carrousel avec 12 éléments, 1 sur 18, de @auteur3, partagée le September 28, 2026",
    ],
)
def test_thumbnail_label_matches_observed_labels(label: str) -> None:
    assert locators.THUMBNAIL_LABEL.match(label)


@pytest.mark.parametrize(
    "label",
    ["Trier et filtrer", "Photo de profil de auteur", "Messages - 1 nouvelle notification"],
)
def test_thumbnail_label_ignores_other_buttons(label: str) -> None:
    assert not locators.THUMBNAIL_LABEL.match(label)
