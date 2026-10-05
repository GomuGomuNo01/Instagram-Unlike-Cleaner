"""Schémas Pydantic : critères d'un nettoyage."""

import re
from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.tables import MediaKind

_USERNAME = re.compile(r"^[a-z0-9._]{1,30}$")


class SortOrder(StrEnum):
    NEWEST_FIRST = "newest_first"
    OLDEST_FIRST = "oldest_first"


class ContentFilter(StrEnum):
    ALL = "all"
    POSTS = "posts"  # photos et carrousels
    REELS = "reels"  # vidéos : celles publiées depuis 2022 sont des Reels


_CONTENT_KINDS: dict[ContentFilter, frozenset[MediaKind]] = {
    ContentFilter.ALL: frozenset(MediaKind),
    ContentFilter.POSTS: frozenset({MediaKind.PHOTO, MediaKind.CAROUSEL}),
    ContentFilter.REELS: frozenset({MediaKind.VIDEO}),
}


class CleanupFilters(BaseModel):
    """Critères d'un nettoyage.

    Le tri et les dates sont appliqués par Instagram, avec le filtre de la page des likes.
    Le type et les auteurs sont appliqués par IUC sur les vignettes collectées, car la
    version web d'Instagram ne propose pas ces filtres. Quand un critère ne peut pas être
    vérifié pour un like (auteur ou type illisible), le like est gardé.
    """

    model_config = ConfigDict(frozen=True)

    sort: SortOrder = SortOrder.NEWEST_FIRST
    start_date: date | None = None
    end_date: date | None = None
    content: ContentFilter = ContentFilter.ALL
    include_authors: tuple[str, ...] = ()  # vide : tous les auteurs
    exclude_authors: tuple[str, ...] = ()

    @field_validator("include_authors", "exclude_authors", mode="before")
    @classmethod
    def _normalize_authors(cls, value: object) -> object:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list | tuple | set | frozenset):
            return value
        authors = set()
        for raw in value:
            author = str(raw).strip().removeprefix("@").lower()
            if not _USERNAME.match(author):
                raise ValueError(f"nom de compte Instagram invalide : {raw!r}")
            authors.add(author)
        return tuple(sorted(authors))

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        today = date.today()
        for value in (self.start_date, self.end_date):
            if value is not None and value > today:
                raise ValueError(f"la date {value:%d/%m/%Y} est dans le futur")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("la date de début doit précéder la date de fin")
        both = set(self.include_authors) & set(self.exclude_authors)
        if both:
            raise ValueError(f"auteur à la fois inclus et exclu : {', '.join(sorted(both))}")
        return self

    @property
    def uses_native_filters(self) -> bool:
        """Vrai si le filtre d'Instagram doit être ouvert (tri inversé ou dates)."""
        return (
            self.sort is not SortOrder.NEWEST_FIRST
            or self.start_date is not None
            or self.end_date is not None
        )

    def matches(self, author: str | None, media_kind: MediaKind | None) -> bool:
        """Applique les critères d'IUC (type et auteurs) à une vignette collectée."""
        if self.content is not ContentFilter.ALL and media_kind not in _CONTENT_KINDS[self.content]:
            return False
        if self.include_authors or self.exclude_authors:
            if author is None:
                return False
            if self.include_authors and author.lower() not in self.include_authors:
                return False
            if author.lower() in self.exclude_authors:
                return False
        return True
