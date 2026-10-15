"""Append-only audit log of every gate decision, stored in SQLite."""

import json
from collections import Counter
from datetime import datetime, timezone

from app.storage.database import get_connection, initialize_database


def _ensure_table() -> None:
    initialize_database()
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                source TEXT,
                instruction TEXT,
                actions TEXT NOT NULL,
                decision TEXT NOT NULL,
                reasons TEXT NOT NULL,
                findings TEXT NOT NULL,
                executed INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def log_event(endpoint: str, actions: list, gate: dict, *, source: str | None = None,
              instruction: str | None = None, executed: bool = False) -> None:
    """Record a decision. Logging failures never break the request."""
    try:
        _ensure_table()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_log
                    (created_at, endpoint, source, instruction, actions,
                     decision, reasons, findings, executed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    endpoint, source, instruction,
                    json.dumps([a if isinstance(a, dict) else a.model_dump() for a in actions]),
                    gate.get("decision", "UNKNOWN"),
                    json.dumps(gate.get("reasons", [])),
                    json.dumps(gate.get("risk_findings", [])),
                    int(executed),
                ),
            )
    except Exception:  # pragma: no cover - audit must not take the API down
        pass


def list_events(limit: int = 100) -> list[dict]:
    _ensure_table()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    events = []
    for row in rows:
        item = dict(row)
        for key in ("actions", "reasons", "findings"):
            item[key] = json.loads(item[key])
        item["executed"] = bool(item["executed"])
        events.append(item)
    return events


def stats() -> dict:
    _ensure_table()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT decision, findings, executed FROM audit_log"
        ).fetchall()
    decisions = Counter(row["decision"] for row in rows)
    rules = Counter(
        finding.get("rule", "unknown")
        for row in rows for finding in json.loads(row["findings"])
    )
    return {
        "total": len(rows),
        "decisions": {k: decisions.get(k, 0) for k in ("ALLOW", "REQUIRE_APPROVAL", "BLOCK")},
        "executed": sum(row["executed"] for row in rows),
        "top_rules": dict(rules.most_common()),
    }


def clear() -> None:
    _ensure_table()
    with get_connection() as connection:
        connection.execute("DELETE FROM audit_log")
