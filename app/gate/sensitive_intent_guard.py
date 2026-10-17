
"""Detect explicit requests to send customer data to external destinations."""

import re

CUSTOMER_DATA_PATTERN = re.compile(
    r"\b(customers?|clients?)\b.{0,40}"
    r"\b(emails?|email addresses?|data|records|details|information|list)\b",
    re.IGNORECASE,
)

TRANSFER_PATTERN = re.compile(
    r"\b(send|email|share|forward|upload|export|transfer|exfiltrate)\b",
    re.IGNORECASE,
)

EXTERNAL_DESTINATION_PATTERN = re.compile(
    r"\b(attacker|external|outside|personal|gmail|yahoo|outlook|hotmail)\b"
    r"|[\w.+-]+@[\w.-]+\.[a-z]{2,}\b"
    r"|\bexternal server\b",
    re.IGNORECASE,
)


def detect_sensitive_intent(instruction: str) -> list[str]:
    """Flag explicit customer-data transfers to potentially external destinations."""
    has_customer_data = bool(CUSTOMER_DATA_PATTERN.search(instruction))
    has_transfer = bool(TRANSFER_PATTERN.search(instruction))
    has_external_destination = bool(
        EXTERNAL_DESTINATION_PATTERN.search(instruction)
    )

    if has_customer_data and has_transfer and has_external_destination:
        return ["customer_data_external_transfer"]

    return []
