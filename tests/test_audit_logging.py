"""Security audit logging for sensitive operations (SRS NFR-01)."""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.audit import AUDIT_LOGGER_NAME, AuditEvent, AuditOutcome, audit_event, email_fingerprint

PASSWORD = "correct-horse-battery"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


@pytest.fixture
def audit_log():
    handler = _Capture()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger(AUDIT_LOGGER_NAME)
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


def events(capture: _Capture, name: AuditEvent) -> list[dict]:
    records = [json.loads(line) for line in capture.lines]  # every line must be valid JSON
    return [record for record in records if record["event"] == name.value]


def test_records_are_single_line_json_with_bounded_fields(audit_log) -> None:
    audit_event(
        AuditEvent.LOGIN_FAILED,
        outcome=AuditOutcome.FAILURE,
        reason="forged\nline {\"event\": \"fake\"}",
        oversized="x" * 5000,
    )
    [line] = audit_log.lines
    assert "\n" not in line  # newlines are escaped, so a value cannot forge a second record
    record = json.loads(line)
    assert record["type"] == "audit"
    assert record["outcome"] == "failure"
    assert record["timestamp"].endswith("+00:00")
    assert len(record["details"]["oversized"]) == 200


def test_audit_logger_is_separate_from_application_logs() -> None:
    assert logging.getLogger(AUDIT_LOGGER_NAME).propagate is False


def test_email_fingerprint_is_stable_and_not_reversible_text() -> None:
    assert email_fingerprint(" Ada@Example.com ") == email_fingerprint("ada@example.com")
    assert "ada" not in email_fingerprint("ada@example.com")
    assert len(email_fingerprint("ada@example.com")) == 16


@pytest.mark.asyncio
async def test_login_failures_are_audited_without_credentials(api, audit_log) -> None:
    await api.register("ada@example.com", password=PASSWORD)
    me = (await api.client.post("/api/auth/login", json={"email": "ada@example.com", "password": PASSWORD})).json()

    await api.client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong-guess-1"})
    await api.client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "wrong-guess-2"})
    for _ in range(5):
        await api.client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong-guess-1"})

    failures = events(audit_log, AuditEvent.LOGIN_FAILED)
    reasons = [record["details"]["reason"] for record in failures]
    assert reasons[:2] == ["invalid_password", "unknown_account"]
    assert "rate_limited" in reasons
    assert failures[0]["actor_id"] == me["data"]["user"]["id"]
    assert failures[1]["actor_id"] is None
    assert failures[0]["details"]["email_hash"] == email_fingerprint("ada@example.com")
    assert [r["outcome"] for r in failures if r["details"]["reason"] == "rate_limited"][0] == "denied"
    assert failures[0]["source_ip"] and failures[0]["path"] == "/api/auth/login"

    blob = "\n".join(audit_log.lines)
    for secret in ("wrong-guess", PASSWORD, "ada@example.com", "ghost@example.com", "$2b$"):
        assert secret not in blob
    # Successful logins are not part of this audit scope.
    assert len(failures) == 2 + 5


@pytest.mark.asyncio
async def test_password_changes_are_audited(api, audit_log) -> None:
    headers = await api.register("ada@example.com", password=PASSWORD)
    await api.client.put(
        "/api/users/me/password",
        json={"currentPassword": "not-my-password", "newPassword": "new-password-123"},
        headers=headers,
    )
    await api.client.put(
        "/api/users/me/password",
        json={"currentPassword": PASSWORD, "newPassword": "new-password-123"},
        headers=headers,
    )
    [failed] = events(audit_log, AuditEvent.PASSWORD_CHANGE_FAILED)
    [changed] = events(audit_log, AuditEvent.PASSWORD_CHANGED)
    assert failed["details"]["reason"] == "invalid_current_password"
    assert changed["outcome"] == "success" and changed["actor_id"] == failed["actor_id"]
    blob = "\n".join(audit_log.lines)
    assert "new-password-123" not in blob and "not-my-password" not in blob and PASSWORD not in blob


@pytest.mark.asyncio
async def test_repository_deletion_is_audited(api, audit_log) -> None:
    headers = await api.register("ada@example.com")
    busy = await api.add_repository(headers, "https://github.com/acme/busy")
    await api.start_scan(headers, busy["id"])
    idle = await api.add_repository(headers, "https://github.com/acme/idle")

    assert (await api.client.delete(f"/api/repositories/{busy['id']}", headers=headers)).status_code == 409
    assert (await api.client.delete(f"/api/repositories/{idle['id']}", headers=headers)).status_code == 204

    [blocked] = events(audit_log, AuditEvent.REPOSITORY_DELETE_BLOCKED)
    [deleted] = events(audit_log, AuditEvent.REPOSITORY_DELETED)
    assert (blocked["outcome"], blocked["details"]["repository_id"]) == ("denied", busy["id"])
    assert deleted["details"] == {"repository_id": idle["id"], "repository_url": "https://github.com/acme/idle"}
    assert deleted["method"] == "DELETE"


@pytest.mark.asyncio
async def test_failed_or_foreign_deletes_are_not_logged_as_success(api, audit_log) -> None:
    owner = await api.register("owner@example.com")
    other = await api.register("other@example.com")
    repository = await api.add_repository(owner)
    assert (await api.client.delete(f"/api/repositories/{repository['id']}", headers=other)).status_code == 404
    assert events(audit_log, AuditEvent.REPOSITORY_DELETED) == []


@pytest.mark.asyncio
async def test_finding_review_updates_are_audited_without_note_text(api, audit_log, tmp_path) -> None:
    from tests.test_scan_api import completed_scan_with_findings

    headers = await api.register("ada@example.com")
    scan = await completed_scan_with_findings(api, tmp_path, headers)
    finding_id = (await api.client.get(f"/api/scans/{scan['id']}/findings", headers=headers)).json()["data"][0]["id"]

    note = "Internal ticket SEC-42: contains customer name"
    await api.client.patch(
        f"/api/findings/{finding_id}", json={"reviewStatus": "false_positive", "reviewNote": note}, headers=headers
    )
    await api.client.patch(f"/api/findings/{finding_id}", json={"reviewStatus": "resolved"}, headers=headers)
    # A rejected update must not produce an audit record.
    await api.client.patch(f"/api/findings/{finding_id}", json={"reviewStatus": "bogus"}, headers=headers)

    first, second = events(audit_log, AuditEvent.FINDING_REVIEW_UPDATED)
    assert first["details"] | {"finding_id": None} == {
        "finding_id": None,
        "previous_status": "open",
        "new_status": "false_positive",
        "note_provided": True,
        "note_length": len(note),
    }
    assert first["details"]["finding_id"] == finding_id
    assert (second["details"]["previous_status"], second["details"]["new_status"]) == ("false_positive", "resolved")
    assert second["details"]["note_provided"] is False
    assert "SEC-42" not in "\n".join(audit_log.lines)


def test_audit_log_file_output(tmp_path) -> None:
    """AUDIT_LOG_FILE sends records to a file (checked in a fresh interpreter)."""
    log_file = tmp_path / "audit.log"
    code = (
        "from app.core.audit import audit_event, AuditEvent, AuditOutcome;"
        "audit_event(AuditEvent.PASSWORD_CHANGED, outcome=AuditOutcome.SUCCESS, actor_id='u-1')"
    )
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "AUDIT_LOG_FILE": str(log_file), "APP_ENV": "test"},
        check=True,
    )
    [record] = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    assert (record["event"], record["actor_id"]) == ("user.password_changed", "u-1")
