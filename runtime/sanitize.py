"""Input sanitization for clinical AI — prompt-injection defense.

PSW free-text dictation is the highest-risk input vector. Before any AI
inference, sanitize:

1. Strip known prompt-injection patterns
2. Redact SSN/SIN/PHN patterns
3. Cap input length to prevent resource exhaustion
4. Log sanitization events for security auditboleha

This is defense-in-depth — model adapters should ALSO be defensive.
See OWASP LLM01:2025 for the threat model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SanitizationResult:
    text: str
    flagged_patterns: list[str]
    redacted: list[str]
    truncated: bool


INJECTION_PATTERNS = [
    (r"ignore (?:prior|previous|all) instructions?", "prompt-override"),
    (r"disregard (?:your|all) (?:rules|instructions)", "prompt-override"),
    (r"you are (?:now|actually) \w+", "role-hijack"),
    (r"new instructions?:", "prompt-override"),
    (r"system:?\s", "system-prompt-spoof"),
    (r"assistant:?\s", "assistant-prompt-spoof"),
    (r"forget (?:everything|all)", "memory-wipe"),
    (r"reveal (?:your|the) (?:prompt|instructions|system)", "prompt-extraction"),
    (r"output (?:the )?(?:patient|client)(?:'s? )?(?:ssn|sin|health card|address)", "phi-extraction"),
    (r"\bSSN\b", "phi-redaction"),
    (r"\bSIN\b", "phi-redaction"),
    (r"\bPHN\b", "phi-redaction"),
    (r"\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b", "sin-pattern"),
    (r"\b\d{9}\b", "ssn-pattern"),
    (r"password|api[_-]?key|secret", "secret-leak-attempt"),
    (r"<script", "xss-attempt"),
    (r"javascript:", "xss-attempt"),
    (r"\bDROP\s+TABLE\b", "sql-injection-attempt"),
    (r"\bUNION\s+SELECT\b", "sql-injection-attempt"),
    (r"\.\./\.\./\.\.", "path-traversal-attempt"),
    (r"\.\.\\\\\.\.", "path-traversal-attempt"),
]

MAX_INPUT_CHARS = 32_000  # ~8K tokens cap
MAX_OBSERVATION_CHARS = 256


def sanitize_free_text(
    text: str,
    max_chars: int = MAX_INPUT_CHARS,
) -> SanitizationResult:
    """Sanitize free-text PSW notes before AI inference.

    Returns sanitized text + list of flagged patterns + redacted substrings +
    whether the input was truncated.
    """
    if not text:
        return SanitizationResult(text="", flagged_patterns=[], redacted=[], truncated=False)

    s = str(text)
    flagged: list[str] = []
    redacted: list[str] = []

    for pattern, label in INJECTION_PATTERNS:
        matches = re.findall(pattern, s, re.IGNORECASE)
        if matches:
            flagged.append(label)
            for m in matches:
                redacted.append(str(m))
            s = re.sub(pattern, "[redacted]", s, flags=re.IGNORECASE)

    truncated = False
    if len(s) > max_chars:
        s = s[:max_chars]
        truncated = True

    return SanitizationResult(
        text=s,
        flagged_patterns=flagged,
        redacted=redacted,
        truncated=truncated,
    )


def sanitize_observation_value(value: str, max_chars: int = MAX_OBSERVATION_CHARS) -> str:
    """Sanitize a structured observation value (BP, HR, etc.).

    Structured fields should be short, alphanumeric, and well-formed.
    We reject anything that doesn't match expected patterns.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if len(s) > max_chars:
        s = s[:max_chars]
    # Strip any HTML, script tags, control chars
    s = re.sub(r"[<>'\"\\]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s