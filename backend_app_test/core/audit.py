"""Structured JSON audit logging for security events (SRS NFR-01).

Each call to ``audit_event`` writes one JSON object per line to the
``app.audit`` logger, kept separate from application logs so it can be
shipped to a SIEM or retained longer. Records never contain passwords,
tokens, review-note text, or raw email addresses; a failed login records a
SHA-256 prefix of the normalized email so repeated attacks on one account can
be correlated without storing who was targeted in clear text.

Output goes to stderr by default; set ``AUDIT_LOG_FILE`` to append to a file.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from fastapi import Request

AUDIT_LOGGER_NAME = "app.audit"
MAX_FIELD_LENGTH = 200


class AuditEvent(StrEnum):
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGED = "user.password_changed"
    PASSWORD_CHANGE_FAILED = "user.password_change_failed"
    REPOSITORY_DELETED = "repository.deleted"
    REPOSITORY_DELETE_BLOCKED = "repository.delete_blocked"
    FINDING_REVIEW_UPDATED = "finding.review_updated"


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    if getattr(logger, "_audit_configured", False):
        return logger
    path = os.getenv("AUDIT_LOG_FILE")
    handler: logging.Handler = (
        logging.FileHandler(path, encoding="utf-8") if path else logging.StreamHandler(sys.stderr)
    )
    # The message is already a complete JSON document.
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # Keep audit records out of the application log stream.
    logger.propagate = False
    logger._audit_configured = True  # type: ignore[attr-defined]
    return logger


audit_logger = _build_logger()


def email_fingerprint(email: str) -> str:
    """Correlation key for an email address that does not reveal it."""
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def _clean(value: Any) -> Any:
    """Bound string sizes; JSON encoding escapes newlines, so lines cannot be forged."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, str):
        return value[:MAX_FIELD_LENGTH]
    if isinstance(value, dict):
        return {str(key)[:64]: _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value[:20]]
    return value


def audit_event(
    event: AuditEvent,
    *,
    outcome: AuditOutcome,
    request: Request | None = None,
    actor_id: uuid.UUID | str | None = None,
    **details: Any,
) -> dict[str, Any]:
    """Write one audit record and return it (useful for tests)."""
    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "type": "audit",
        "event": event.value,
        "outcome": outcome.value,
        "actor_id": _clean(actor_id) if actor_id is not None else None,
    }
    if request is not None:
        record["source_ip"] = request.client.host if request.client else None
        record["user_agent"] = _clean(request.headers.get("user-agent", ""))
        record["method"] = request.method
        record["path"] = request.url.path
    record["details"] = _clean(details)
    audit_logger.info(json.dumps(record, sort_keys=True, ensure_ascii=True))
    return record
