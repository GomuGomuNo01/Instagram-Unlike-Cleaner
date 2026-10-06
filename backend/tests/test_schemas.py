from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.models.schemas import CleanupFilters, SortOrder


def test_default_filters_target_everything_without_native_filter() -> None:
    assert not CleanupFilters().uses_native_filters


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


def test_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError, match="précéder"):
        CleanupFilters(start_date=date(2025, 1, 2), end_date=date(2025, 1, 1))


def test_rejects_future_dates() -> None:
    with pytest.raises(ValidationError, match="futur"):
        CleanupFilters(end_date=date.today() + timedelta(days=1))


def test_filters_survive_a_json_round_trip() -> None:
    filters = CleanupFilters(
        sort=SortOrder.OLDEST_FIRST, start_date=date(2019, 1, 1), end_date=date(2024, 1, 1)
    )

    assert CleanupFilters.model_validate(filters.model_dump(mode="json")) == filters


def test_filters_saved_before_the_redesign_stay_readable() -> None:
    """Les nettoyages enregistrés avec l'ancien affinage (type, comptes) restent lisibles :
    seul le filtre d'Instagram est conservé."""
    saved = {
        "sort": "oldest_first",
        "start_date": "2021-01-01",
        "end_date": None,
        "content": "reels",
        "include_authors": [],
        "exclude_authors": ["auteur_a"],
    }

    filters = CleanupFilters.model_validate(saved)

    assert filters == CleanupFilters(sort=SortOrder.OLDEST_FIRST, start_date=date(2021, 1, 1))
    assert "content" not in filters.model_dump()
