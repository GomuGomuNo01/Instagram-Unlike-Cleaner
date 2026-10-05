"""Connexion à la base SQLite locale et création des tables au démarrage."""

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, event, inspect
from sqlalchemy.engine import URL
from sqlmodel import SQLModel, create_engine

import app.models.tables  # noqa: F401  (enregistre les tables dans SQLModel.metadata)


class OutdatedSchemaError(RuntimeError):
    """La base locale a été créée par une version précédente, aux colonnes différentes."""


def make_engine(db_path: Path) -> Engine:
    # URL.create gère les chemins avec espaces, contrairement à une URL écrite à la main.
    url = URL.create("sqlite", database=str(db_path))
    # check_same_thread=False : l'API et le moteur partagent la base depuis des threads différents.
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")  # SQLite ignore les clés étrangères par défaut
    cursor.execute("PRAGMA journal_mode=WAL")  # l'API peut lire pendant que le moteur écrit
    cursor.close()


def init_db(engine: Engine) -> None:
    """Crée les tables manquantes, puis vérifie que les tables existantes sont à jour.

    Le projet n'a pas d'outil de migration : une base d'une version précédente est signalée
    clairement plutôt que de provoquer plus tard une erreur SQL obscure.
    """
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    for table in SQLModel.metadata.sorted_tables:
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        expected = {column.name for column in table.columns}
        if existing != expected:
            raise OutdatedSchemaError(
                f"La base locale ({engine.url.database}) date d'une version précédente d'IUC "
                f"(table « {table.name} » différente). Supprime ce fichier puis relance : "
                "il sera recréé vide."
            )
