
import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "action_gate.db"


def get_connection():
    """Open a connection to the local SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the demo customer table if it doesn't exist."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
            """
        )


def seed_customers():
    """Insert reproducible demo records without duplicating seed data."""
    initialize_database()

    sample_customers = [
        (1, "Ayesha Khan", "ayesha@example.com", "active"),
        (2, "Ali Ahmed", "ali@example.com", "active"),
        (3, "Ayesha Khan", "ayesha@example.com", "active"),
        (4, "Sara Malik", "sara@example.com", "active"),
        (5, "Ali Ahmed", "ali@example.com", "active"),
    ]

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO customers (id, name, email, status)
            VALUES (?, ?, ?, ?)
            """,
            sample_customers,
        )


def get_customers():
    """Return all customer records as dictionaries."""
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, email, status FROM customers ORDER BY id"
        ).fetchall()

    return [dict(row) for row in rows]
