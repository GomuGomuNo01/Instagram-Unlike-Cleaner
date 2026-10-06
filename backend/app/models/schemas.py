"""Schémas Pydantic : critères d'un nettoyage."""

from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SortOrder(StrEnum):
    NEWEST_FIRST = "newest_first"
    OLDEST_FIRST = "oldest_first"


class CleanupFilters(BaseModel):
    """Critères d'un nettoyage : le filtre d'Instagram, tel que le propose Instagram web dans
    le panneau « Trier et filtrer » de la page des likes (tri, date de début et date de fin
    du like). IUC applique ces critères en remplissant ce panneau ; il n'en ajoute aucun.

    Les champs inconnus sont ignorés : les nettoyages enregistrés avant la refonte du
    filtrage (type de contenu, comptes) restent lisibles.
    """

    model_config = ConfigDict(frozen=True)

    sort: SortOrder = Field(default=SortOrder.NEWEST_FIRST, description="« Trier par ».")
    start_date: date | None = Field(
        default=None, description="Date de début, date du like (vide : sans limite)."
    )
    end_date: date | None = Field(
        default=None, description="Date de fin, date du like (vide : aujourd'hui)."
    )

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        today = date.today()
        for value in (self.start_date, self.end_date):
            if value is not None and value > today:
                raise ValueError(f"la date {value:%d/%m/%Y} est dans le futur")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("la date de début doit précéder la date de fin")
        return self

    @property
    def uses_native_filters(self) -> bool:
        """Vrai si le panneau d'Instagram doit être ouvert (tri inversé ou dates)."""
        return (
            self.sort is not SortOrder.NEWEST_FIRST
            or self.start_date is not None
            or self.end_date is not None
        )
