import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "migrations"


def connect(database: str | Path = ":memory:") -> sqlite3.Connection:
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    migration = (MIGRATIONS / "001_initial.sql").read_text(encoding="utf-8")
    connection.executescript(migration)
    connection.commit()