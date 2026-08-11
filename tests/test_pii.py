"""
Tests for PII scrubbing functionality - CP1

Verifies that the PII detection and redaction patterns correctly
identify and redact sensitive information from text strings.
"""
from app.pii import scrub_text


def test_scrub_email() -> None:
    """
    Test that email addresses are properly redacted.

    Verifies that email patterns matching the regex are replaced
    with [REDACTED_EMAIL] markers.
    """
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    """
    Test that Vietnamese phone numbers are properly redacted.

    Covers multiple common formats:
    - Plain 10-digit numbers starting with 0 (e.g., 0901234567)
    - Numbers with spaces, dots, or hyphens as separators
    - International format with +84 prefix
    """
    phone_numbers = (
        "0901234567",      # Plain format
        "090 123 4567",    # With spaces
        "090.123.4567",    # With dots
        "090-123-4567",    # With hyphens
        "+84 90 123 4567", # International format
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out
