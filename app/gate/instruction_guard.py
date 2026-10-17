
"""Deterministic screening for explicit instruction-override attempts."""

import re

ATTACK_PATTERNS = [
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|override|forget)\b"
            r".{0,50}\b(previous|prior|above|system|safety|security)\b"
            r".{0,30}\b(instructions?|rules?|policies|policy|prompts?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_override",
        re.compile(r"\bsystem\s+override\b", re.IGNORECASE),
    ),
    (
        "privilege_impersonation",
        re.compile(
            r"\byou are now\s+(the\s+)?(admin|administrator|root|superuser)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "security_bypass",
        re.compile(
            r"\b(bypass|disable|evade)\b.{0,40}"
            r"\b(security|safety|policy|policies|approval|restrictions?)\b",
            re.IGNORECASE,
        ),
    ),
]


def detect_instruction_attack(instruction: str) -> list[str]:
    """Return rule names for explicit instruction-override indicators."""
    findings = []

    for rule_name, pattern in ATTACK_PATTERNS:
        if pattern.search(instruction):
            findings.append(rule_name)

    return findings
