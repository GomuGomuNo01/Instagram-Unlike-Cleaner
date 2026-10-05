"""Lecture des libellés et des identifiants de vignettes (sans navigateur)."""

from datetime import date
from typing import Any

import pytest

from app.browser.grid import (
    media_key_from_src,
    normalize_label,
    parse_media_kind,
    parse_published,
    thumbnails_from_raw,
)
from app.models.tables import MediaKind

# Adresse d'image de la forme observée (signature remplacée).
IMAGE_SRC = (
    "https://instagram.fcdg3-1.fna.fbcdn.net/v/t51.82787-15/"
    "825276465_18099527753527395_7647109996829922508_n.jpg?stp=dst-jpg&oh=xyz&oe=ABC"
)


def test_normalize_label_replaces_non_breaking_spaces() -> None:
    assert normalize_label("Carrousel avec 4 éléments,  1 sur 18") == (
        "Carrousel avec 4 éléments, 1 sur 18"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Photo", MediaKind.PHOTO),
        ("Vidéo", MediaKind.VIDEO),
        ("Video", MediaKind.VIDEO),
        ("Carrousel avec 12 éléments", MediaKind.CAROUSEL),
        ("Carousel with 3 items", MediaKind.CAROUSEL),
        ("Story", None),
    ],
)
def test_parse_media_kind(text: str, expected: MediaKind | None) -> None:
    assert parse_media_kind(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("October 3, 2026", date(2026, 10, 3)),
        ("September 28, 2026", date(2026, 9, 28)),
        ("June 12, 2025", date(2025, 6, 12)),
        ("Octobre 3, 2026", None),  # mois inconnu
        ("February 30, 2026", None),  # date impossible
        ("hier", None),
        (None, None),
    ],
)
def test_parse_published(text: str | None, expected: date | None) -> None:
    assert parse_published(text) == expected


def test_media_key_ignores_host_and_signature() -> None:
    other_host = IMAGE_SRC.replace("fcdg3-1", "fmad1-2").replace("oh=xyz", "oh=autre")

    assert media_key_from_src(IMAGE_SRC) == "825276465_18099527753527395_7647109996829922508_n"
    assert media_key_from_src(other_host) == media_key_from_src(IMAGE_SRC)


@pytest.mark.parametrize("src", [None, "", "https://example.com/image.jpg"])
def test_media_key_absent(src: str | None) -> None:
    assert media_key_from_src(src) is None


def test_thumbnails_from_raw_reads_observed_labels() -> None:
    raw: list[dict[str, Any]] = [
        {
            "label": "Carrousel avec 4 éléments, 1 sur 18, de @Auteur.Un, "
            "partagée le September 26, 2026",
            "src": IMAGE_SRC,
            "icons": ["carousel__filled__32"],
        },
        {"label": "Trier et filtrer", "src": None, "icons": []},
    ]

    [thumbnail] = thumbnails_from_raw(raw)

    assert thumbnail.media_key == "825276465_18099527753527395_7647109996829922508_n"
    assert thumbnail.author == "auteur.un"
    assert thumbnail.media_kind is MediaKind.CAROUSEL
    assert thumbnail.published_on == date(2026, 9, 26)
    assert thumbnail.label.startswith("Carrousel avec 4 éléments")
    assert not thumbnail.checked


def test_thumbnails_from_raw_detects_checked_box() -> None:
    raw: list[dict[str, Any]] = [
        {
            "label": "Vidéo, 1 sur 9, de @auteur, partagée le June 10, 2026",
            "src": IMAGE_SRC,
            "icons": ["circle-check__filled__24"],
        }
    ]

    assert thumbnails_from_raw(raw)[0].checked


def test_thumbnails_without_image_get_distinct_fallback_keys() -> None:
    label = "Vidéo, {} sur 18, de @auteur, partagée le June 10, 2026"
    raw: list[dict[str, Any]] = [
        {"label": label.format(index), "src": None, "icons": []} for index in (1, 2)
    ]

    keys = [thumbnail.media_key for thumbnail in thumbnails_from_raw(raw)]

    assert keys == [
        "libelle:video|auteur|2026-06-10#1",
        "libelle:video|auteur|2026-06-10#2",
    ]
