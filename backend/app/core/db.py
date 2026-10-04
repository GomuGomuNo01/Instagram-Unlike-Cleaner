"""Connexion à la base SQLite locale et création des tables au démarrage."""

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy.engine import URL
from sqlmodel import SQLModel, create_engine

import app.models.tables  # noqa: F401  (enregistre les tables dans SQLModel.metadata)


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
    """Crée les tables manquantes. Sans effet sur une base déjà initialisée."""
    SQLModel.metadata.create_all(engine)
