from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.models.schemas import CleanupFilters, ContentFilter, SortOrder
from app.models.tables import MediaKind


def test_default_filters_target_everything_without_native_filter() -> None:
    filters = CleanupFilters()

    assert not filters.uses_native_filters
    assert filters.matches("auteur", MediaKind.VIDEO)
    assert filters.matches(None, None)


@pytest.mark.parametrize(
    "filters",
    [
        CleanupFilters(sort=SortOrder.OLDEST_FIRST),
        CleanupFilters(start_date=date(2024, 1, 1)),
        CleanupFilters(end_date=date(2024, 1, 1)),
    ],
)
def test_sort_and_dates_use_instagram_filter(filters: CleanupFilters) -> None:
    assert filters.uses_native_filters


def test_authors_are_normalized() -> None:
    filters = CleanupFilters(include_authors=(" @Auteur_A ", "auteur_a", "B.compte"))

    assert filters.include_authors == ("auteur_a", "b.compte")


@pytest.mark.parametrize("author", ["deux mots", "a" * 31, "@", "accent_é"])
def test_rejects_invalid_author(author: str) -> None:
    with pytest.raises(ValidationError, match="nom de compte"):
        CleanupFilters(exclude_authors=(author,))


def test_rejects_author_both_included_and_excluded() -> None:
    with pytest.raises(ValidationError, match="inclus et exclu"):
        CleanupFilters(include_authors=("auteur",), exclude_authors=("@Auteur",))


def test_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError, match="précéder"):
        CleanupFilters(start_date=date(2025, 1, 2), end_date=date(2025, 1, 1))


def test_rejects_future_dates() -> None:
    with pytest.raises(ValidationError, match="futur"):
        CleanupFilters(end_date=date.today() + timedelta(days=1))


@pytest.mark.parametrize(
    ("content", "kind", "expected"),
    [
        (ContentFilter.POSTS, MediaKind.PHOTO, True),
        (ContentFilter.POSTS, MediaKind.CAROUSEL, True),
        (ContentFilter.POSTS, MediaKind.VIDEO, False),
        (ContentFilter.REELS, MediaKind.VIDEO, True),
        (ContentFilter.REELS, MediaKind.PHOTO, False),
        (ContentFilter.REELS, None, False),  # type illisible : on garde le like
    ],
)
def test_content_filter(content: ContentFilter, kind: MediaKind | None, expected: bool) -> None:
    assert CleanupFilters(content=content).matches("auteur", kind) is expected


def test_include_authors_targets_only_them() -> None:
    filters = CleanupFilters(include_authors=("auteur_a",))

    assert filters.matches("Auteur_A", MediaKind.PHOTO)
    assert not filters.matches("auteur_b", MediaKind.PHOTO)


def test_exclude_authors_are_never_targeted() -> None:
    filters = CleanupFilters(exclude_authors=("auteur_a",))

    assert not filters.matches("auteur_a", MediaKind.PHOTO)
    assert filters.matches("auteur_b", MediaKind.PHOTO)
    assert not filters.matches(None, MediaKind.PHOTO)  # auteur illisible : on garde le like


def test_filters_survive_a_json_round_trip() -> None:
    filters = CleanupFilters(
        sort=SortOrder.OLDEST_FIRST,
        end_date=date(2024, 1, 1),
        content=ContentFilter.REELS,
        exclude_authors=("auteur_a",),
    )

    assert CleanupFilters.model_validate(filters.model_dump(mode="json")) == filters
