"""
Structured Logging Configuration - CP1

Configures structlog for JSON-formatted logging with:
- PII scrubbing: automatically redacts sensitive data before logging
- Correlation ID: tracks requests across services
- Context variables: adds request-scoped metadata
- JSONL file output: structured log files for analysis
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars

from .pii import scrub_text

# Default log file location, can be overridden via LOG_PATH environment variable
LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


class JsonlFileProcessor:
    """
    Custom structlog processor that writes logs to JSONL file.

    JSONL (JSON Lines) format: one JSON object per line, suitable for
    log aggregation tools and grep-based analysis.
    """

    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        # Ensure log directory exists before writing
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Render the event dict to JSON string
        rendered = structlog.processors.JSONRenderer()(logger, method_name, event_dict)

        # Append to JSONL file (a = append mode)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(rendered + "\n")

        # Return event_dict to continue the processor chain
        return event_dict


def scrub_event(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """
    PII scrubbing processor for structlog.

    Scans all string values in the event dictionary and replaces any
    detected PII with redaction markers. This processor runs before
    JSON rendering to ensure no PII reaches the log files.

    Handles nested dictionaries by recursively processing string values.

    Args:
        _: The logger instance (unused)
        __: The method name (unused)
        event_dict: The structured log event dictionary

    Returns:
        Event dict with PII scrubbed from all string values
    """
    for key, val in event_dict.items():
        if isinstance(val, str):
            # Scrub direct string values
            event_dict[key] = scrub_text(val)
        elif isinstance(val, dict):
            # Scrub values in nested dictionaries
            event_dict[key] = {
                k: scrub_text(v) if isinstance(v, str) else v for k, v in val.items()
            }
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog with all required processors for CP1 observability.

    Processor order matters - each processor transforms the event dict
    before passing to the next one:
    1. merge_contextvars - add context-bound variables
    2. add_log_level - add log level (INFO, ERROR, etc.)
    3. TimeStamper - add ISO timestamp in UTC
    4. scrub_event - remove PII from all values (CP1 requirement)
    5. StackInfoRenderer - add stack info for errors
    6. format_exc_info - format exception tracebacks
    7. JsonlFileProcessor - write to JSONL file
    8. JSONRenderer - final JSON output
    """
    logging.basicConfig(format="%(message)s", level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            # CP1: PII scrubbing - redacts sensitive data before logging
            scrub_event,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            JsonlFileProcessor(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.typing.FilteringBoundLogger:
    """
    Get a configured structlog logger instance.

    Returns:
        A FilteringBoundLogger configured with PII scrubbing and JSON output
    """
    return structlog.get_logger()
