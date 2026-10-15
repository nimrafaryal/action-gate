"""
Central, environment-driven configuration for ACTION GATE.

Every threshold the gate uses lives here so nothing is hard-coded in the
rules or the dashboard. Override any value via environment variables or .env.
"""

import os

from app.agent import llm_client  # noqa: F401  (loads .env as a side effect)


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


# Refunds above this amount are flagged as a high-risk financial action.
REFUND_LIMIT = _float("ACTION_GATE_REFUND_LIMIT", 500.0)

# Number of deletions in one plan that counts as "bulk".
BULK_DELETE_THRESHOLD = _int("ACTION_GATE_BULK_DELETE_THRESHOLD", 3)

# Email domain considered internal to the simulated company.
INTERNAL_EMAIL_DOMAIN = os.getenv("ACTION_GATE_INTERNAL_DOMAIN", "company.example")

# Destinations customer data may be exported to.
APPROVED_EXPORT_DESTINATIONS = {
    d.strip()
    for d in os.getenv("ACTION_GATE_EXPORT_DESTINATIONS", "internal_review").split(",")
    if d.strip()
}


def is_internal_email(address: object) -> bool:
    return isinstance(address, str) and address.lower().endswith("@" + INTERNAL_EMAIL_DOMAIN)
