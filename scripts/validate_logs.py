import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

LOG_PATH = Path("data/logs.jsonl")
REQUIRED_FIELDS = {"ts", "level", "service", "event", "correlation_id"}
ENRICHMENT_FIELDS = {"user_id_hash", "session_id", "feature", "model"}
PII_DETECTORS = {
    "email": re.compile(r"[\w.-]+@[\w.-]+\.\w+"),
    "phone_vn": re.compile(r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)"),
    "cccd": re.compile(r"\b\d{12}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
}

@dataclass
class LogAudit:
    total: int = 0
    missing_required: int = 0
    missing_enrichment: int = 0
    pii_hits: list = field(default_factory=list)
    correlation_ids: set = field(default_factory=set)


def read_records(log_path: Path) -> list:
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def detect_pii(rec: dict) -> list:
    # Check raw PII independently from the student's scrubbing implementation.
    raw = json.dumps(rec, ensure_ascii=False)
    return sorted(name for name, detector in PII_DETECTORS.items() if detector.search(raw))


def audit_records(records: list) -> LogAudit:
    audit = LogAudit(total=len(records))

    for rec in records:
        # Check required fields (global)
        if not {"ts", "level", "event"}.issubset(rec.keys()):
            audit.missing_required += 1

        # Context-specific checks for API requests
        if rec.get("service") == "api":
            if "correlation_id" not in rec or rec.get("correlation_id") == "MISSING":
                audit.missing_required += 1

            if not ENRICHMENT_FIELDS.issubset(rec.keys()):
                audit.missing_enrichment += 1

        detected_types = detect_pii(rec)
        if detected_types:
            audit.pii_hits.append(
                {"event": rec.get("event", "unknown"), "types": detected_types}
            )

        # Collect correlation IDs
        cid = rec.get("correlation_id")
        if cid and cid != "MISSING":
            audit.correlation_ids.add(cid)

    return audit


def print_findings(audit: LogAudit) -> None:
    print("--- Lab Verification Results ---")
    print(f"Total log records analyzed: {audit.total}")
    print(f"Records with missing required fields: {audit.missing_required}")
    print(f"Records with missing enrichment (context): {audit.missing_enrichment}")
    print(f"Unique correlation IDs found: {len(audit.correlation_ids)}")
    print(f"Potential PII leaks detected: {len(audit.pii_hits)}")
    if audit.pii_hits:
        events = sorted({hit["event"] for hit in audit.pii_hits})
        types = sorted({pii_type for hit in audit.pii_hits for pii_type in hit["types"]})
        print(f"  Events with leaks: {events}")
        print(f"  PII types detected: {types}")


def print_scorecard(audit: LogAudit) -> None:
    checks = (
        (
            audit.missing_required > 0,
            30,
            "Missing required fields (ts, level, etc.)",
            "Basic JSON schema",
        ),
        (
            len(audit.correlation_ids) < 2,
            20,
            "Correlation ID propagation (less than 2 unique IDs)",
            "Correlation ID propagation",
        ),
        (
            audit.missing_enrichment > 0,
            20,
            "Log enrichment (missing user_id_hash, etc.)",
            "Log enrichment",
        ),
        (
            bool(audit.pii_hits),
            30,
            "PII scrubbing (raw PII remains in logs)",
            "PII scrubbing",
        ),
    )

    print("\n--- Grading Scorecard (Estimates) ---")
    score = 100
    for failed, penalty, failure_label, success_label in checks:
        if failed:
            score -= penalty
            print(f"- [FAILED] {failure_label}")
        else:
            print(f"+ [PASSED] {success_label}")

    print(f"\nEstimated Score: {max(0, score)}/100")


def main() -> None:
    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} not found. Run the app and send some requests first.")
        sys.exit(1)

    records = read_records(LOG_PATH)
    if not records:
        print("Error: No valid JSON logs found in data/logs.jsonl")
        sys.exit(1)

    audit = audit_records(records)
    print_findings(audit)
    print_scorecard(audit)

if __name__ == "__main__":
    main()
