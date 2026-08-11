"""
PII (Personally Identifiable Information) Scrubbing Module - CP1

This module handles detection and redaction of sensitive personal information
to prevent PII leaks in logs. All patterns use regex matching to identify
and replace sensitive data with redaction markers.
"""
from __future__ import annotations

import hashlib
import re

# -----------------------------------------------------------------------------
# PII Pattern Definitions
# Each pattern targets a specific type of sensitive information commonly
# found in Vietnamese systems. Patterns are compiled at module load time
# for performance.
# -----------------------------------------------------------------------------

PII_PATTERNS: dict[str, str] = {
    # Email addresses: matches common email formats (user@domain.tld)
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",

    # Vietnamese phone numbers: matches formats like 0xxx, +84xxx, with optional separators
    # (?<!\d) and (?!\d) ensure we don't match partial numbers
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .\-]?\d){9}(?!\d)",

    # CCCD (Vietnamese Citizen Identification Card): exactly 12 digits
    "cccd": r"\b\d{12}\b",

    # Credit card numbers: 16 digits with optional hyphens/spaces
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",

    # Passport: Vietnamese format (1 letter + 7-8 digits)
    "passport": r"\b[A-Z]\d{7,8}\b",

    # Vietnamese address keywords: common address components in Vietnamese text
    "address_vn": r"\b(?:số nhà|đường|phường|quận|huyện|tỉnh|thành phố)\b",
}


def scrub_text(text: str) -> str:
    """
    Scrub all PII from a text string.

    Iterates through all defined PII patterns and replaces matches with
    redacted markers like [REDACTED_EMAIL], [REDACTED_PHONE_VN], etc.

    Args:
        text: Input text that may contain PII

    Returns:
        Text with all PII replaced by redaction markers
    """
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    """
    Create a safe summary of text for logging/debugging.

    First scrubs PII, then truncates to max_len characters.
    Used for creating log-safe representations of user inputs.

    Args:
        text: Input text to summarize
        max_len: Maximum length of output (default 80)

    Returns:
        Scrubbed and truncated text with "..." suffix if truncated
    """
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    """
    Hash user ID for anonymous identification.

    Uses SHA-256 truncated to 12 characters to identify users without
    exposing their actual user ID in logs.

    Args:
        user_id: The original user identifier

    Returns:
        12-character hex hash of the user ID
    """
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
