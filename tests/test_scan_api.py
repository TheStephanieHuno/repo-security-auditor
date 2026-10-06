"""RSA-92 (T-32a, T-32b): scan dispatch, progress polling, cancellation, and review persistence."""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import ClassVar

import pytest
from sqlalchemy import func, select

from app.db.models import (
    Confidence,
    EvidenceType,
    Finding,
    FindingCategory,
    Report,
    Scan,
    ScannerName,
    ScannerRun,
    Severity,
)
from app.db.normalization import NormalizedEvidence, NormalizedFinding, build_fingerprint
from app.scanners.base import CheckError, SecurityCheck
from app.services.scan_runner import run_scan_job


def make_finding(severity: Severity, index: int, scanner: str = "SEMGREP") -> NormalizedFinding:
    return NormalizedFinding(
        category=FindingCategory.CODE,
        source_scanner=scanner,
        rule_id=f"rule-{index}",
        title=f"Finding {index}",
        description="Untrusted input reaches a dangerous sink.",
        severity=severity,
        confidence=Confidence.HIGH,
        recommendation="Validate the input.",
        fingerprint=build_fingerprint(
            source_scanner=scanner, rule_id=f"rule-{index}", category=FindingCategory.CODE,
            file_path="src/app.py", line_start=index, stable_resource=None, title=f"Finding {index}",
        ),
        file_path="src/app.py",
        line_start=index,
        line_end=index,
        evidence=(NormalizedEvidence(evidence_type=EvidenceType.CODE, file_path="src/app.py",
                                     line_start=index, line_end=index, code_snippet="eval(x)"),),
    )


def fake_check(scanner: ScannerName, *, findings=(), error: str | None = None, crash: bool = False):
    class FakeCheck(SecurityCheck):
        name: ClassVar[ScannerName] = scanner

        async def scan(self, workspace: Path):
            assert workspace.is_dir()
            if crash:
                raise RuntimeError("boom with secret token=abc123")
            if error:
                raise CheckError(error)
            return list(findings)

    return FakeCheck()


def fake_workspace(tmp_path: Path):
    @asynccontextmanager
    async def factory(url: str, branch: str, commit_sha: str | None):
        workspace = tmp_path / "repo"
        workspace.mkdir(exist_ok=True)
        yield workspace

    return factory


async def run_job(api, scan_db_id: int, tmp_path: Path, checks) -> None:
    await run_scan_job(
        scan_db_id,
        session_factory=api.sessions,
        checks_factory=lambda: checks,
        workspace_factory=fake_workspace(tmp_path),
        ai_factory=lambda: None,
    )


async def scan_db_id(api, public_id: str) -> int:
    async with api.sessions() as db:
        return (await db.execute(select(Scan.id).where(Scan.public_id == uuid.UUID(public_id)))).scalar_one()


ALL_PASSING = lambda: [  # noqa: E731
    fake_check(ScannerName.GITLEAKS),
    fake_check(ScannerName.SEMGREP, findings=[make_finding(Severity.HIGH, 1), make_finding(Severity.LOW, 2)]),
    fake_check(ScannerName.OSV),
    fake_check(ScannerName.CONFIG, findings=[make_finding(Severity.CRITICAL, 3, "CONFIG")]),
]


@pytest.mark.asyncio
async def test_start_scan_persists_queued_scan_and_dispatches(api) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"], branch="develop")

    assert scan["status"] == "queued"
    assert scan["progress"] == 0
    assert scan["branch"] == "develop"
    assert scan["repositoryId"] == repository["id"]
    internal_id = await scan_db_id(api, scan["id"])
    assert api.dispatcher.dispatched == [internal_id]
    async with api.sessions() as db:
        names = set((await db.execute(select(ScannerRun.scanner_name).where(ScannerRun.scan_id == internal_id))).scalars())
    assert names == {"GITLEAKS", "SEMGREP", "OSV", "CONFIG"}


@pytest.mark.asyncio
@pytest.mark.parametrize("branch", ["--upload-pack=evil", "main;rm -rf /", "../x", "", "a" * 300])
async def test_start_scan_rejects_unsafe_branch_names(api, branch) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    response = await api.client.post(
        "/api/scans", json={"repositoryId": repository["id"], "branch": branch}, headers=headers
    )
    assert response.status_code == 422
    assert api.dispatcher.dispatched == []


@pytest.mark.asyncio
async def test_progress_polling_through_worker_lifecycle(api, tmp_path) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"])
    status_url = f"/api/scans/{scan['id']}/status"

    queued = (await api.client.get(status_url, headers=headers)).json()["data"]
    assert (queued["status"], queued["progress"]) == ("queued", 0)

    await run_job(api, await scan_db_id(api, scan["id"]), tmp_path, ALL_PASSING())

    done = (await api.client.get(status_url, headers=headers)).json()["data"]
    assert (done["status"], done["progress"]) == ("completed", 100)
    detail = (await api.client.get(f"/api/scans/{scan['id']}", headers=headers)).json()["data"]
    assert detail["findingsCount"] == {"critical": 1, "high": 1, "medium": 0, "low": 1, "info": 0}
    assert detail["startedAt"] and detail["completedAt"]
    async with api.sessions() as db:
        assert await db.scalar(select(func.count(Report.id))) == 1  # report generated after completion


@pytest.mark.asyncio
async def test_running_scan_reports_partial_progress(api) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"])
    async with api.sessions() as db:
        from app.db.lifecycle import mark_scan_running, mark_scanner_run_running, record_scanner_run_success

        row = (await db.execute(select(Scan).where(Scan.public_id == uuid.UUID(scan["id"])))).scalar_one()
        await mark_scan_running(db, scan=row)
        runs = list((await db.execute(select(ScannerRun).where(ScannerRun.scan_id == row.id))).scalars())
        for run in runs:
            await mark_scanner_run_running(db, scanner_run=run)
        await record_scanner_run_success(db, scanner_run=runs[0], findings=[])
        await db.commit()
    progress = (await api.client.get(f"/api/scans/{scan['id']}/status", headers=headers)).json()["data"]
    assert progress["status"] == "running"
    assert progress["progress"] == 25


@pytest.mark.asyncio
async def test_one_failing_scanner_keeps_other_results(api, tmp_path) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"])
    checks = [
        fake_check(ScannerName.GITLEAKS, crash=True),
        fake_check(ScannerName.SEMGREP, findings=[make_finding(Severity.HIGH, 1)]),
        fake_check(ScannerName.OSV, error="OSV API unavailable (HTTP 503)"),
        fake_check(ScannerName.CONFIG),
    ]
    await run_job(api, await scan_db_id(api, scan["id"]), tmp_path, checks)

    detail = (await api.client.get(f"/api/scans/{scan['id']}", headers=headers)).json()["data"]
    assert detail["status"] == "completed"  # PARTIAL is exposed as completed with results
    assert detail["findingsCount"]["high"] == 1
    async with api.sessions() as db:
        runs = {r.scanner_name: r for r in (await db.execute(select(ScannerRun))).scalars()}
        scan_row = (await db.execute(select(Scan))).scalar_one()
    assert scan_row.status == "PARTIAL"
    assert runs["GITLEAKS"].status == "FAILED"
    assert "abc123" not in (runs["GITLEAKS"].error_summary or "")  # crash details stay out of the DB
    assert runs["OSV"].error_summary == "OSV API unavailable (HTTP 503)"


@pytest.mark.asyncio
async def test_workspace_failure_fails_every_scanner(api, tmp_path) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"])

    @asynccontextmanager
    async def failing_workspace(url, branch, sha):
        raise CheckError("repository clone failed: branch not found")
        yield  # pragma: no cover

    await run_scan_job(
        await scan_db_id(api, scan["id"]),
        session_factory=api.sessions,
        checks_factory=ALL_PASSING,
        workspace_factory=failing_workspace,
        ai_factory=lambda: None,
    )
    detail = (await api.client.get(f"/api/scans/{scan['id']}", headers=headers)).json()["data"]
    assert detail["status"] == "failed"


@pytest.mark.asyncio
async def test_duplicate_job_delivery_creates_no_duplicates(api, tmp_path) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"])
    internal_id = await scan_db_id(api, scan["id"])
    await run_job(api, internal_id, tmp_path, ALL_PASSING())
    await run_job(api, internal_id, tmp_path, ALL_PASSING())
    async with api.sessions() as db:
        assert await db.scalar(select(func.count(Finding.id))) == 3
        assert await db.scalar(select(func.count(Report.id))) == 1


@pytest.mark.asyncio
async def test_cancel_scan_and_late_results_are_ignored(api, tmp_path) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"])

    cancelled = await api.client.post(f"/api/scans/{scan['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    body = cancelled.json()["data"]
    assert body["status"] == "cancelled" and body["cancelledAt"]

    again = await api.client.post(f"/api/scans/{scan['id']}/cancel", headers=headers)
    assert again.status_code == 409

    await run_job(api, await scan_db_id(api, scan["id"]), tmp_path, ALL_PASSING())
    status = (await api.client.get(f"/api/scans/{scan['id']}/status", headers=headers)).json()["data"]
    assert status["status"] == "cancelled"
    async with api.sessions() as db:
        assert await db.scalar(select(func.count(Finding.id))) == 0


@pytest.mark.asyncio
async def test_scan_history_and_listing_filters(api) -> None:
    headers = await api.register("ada@example.com")
    first_repo = await api.add_repository(headers, "https://github.com/acme/one")
    second_repo = await api.add_repository(headers, "https://github.com/acme/two")
    await api.start_scan(headers, first_repo["id"])
    await api.start_scan(headers, first_repo["id"])
    await api.start_scan(headers, second_repo["id"])

    all_scans = (await api.client.get("/api/scans", headers=headers)).json()
    assert all_scans["pagination"]["totalItems"] == 3
    filtered = (await api.client.get(f"/api/scans?repositoryId={first_repo['id']}", headers=headers)).json()
    assert filtered["pagination"]["totalItems"] == 2
    assert {s["repositoryId"] for s in filtered["data"]} == {first_repo["id"]}


async def completed_scan_with_findings(api, tmp_path, headers):
    repository = await api.add_repository(headers)
    scan = await api.start_scan(headers, repository["id"])
    await run_job(api, await scan_db_id(api, scan["id"]), tmp_path, ALL_PASSING())
    return scan


@pytest.mark.asyncio
async def test_findings_listing_and_filters(api, tmp_path) -> None:
    headers = await api.register("ada@example.com")
    scan = await completed_scan_with_findings(api, tmp_path, headers)

    findings = (await api.client.get(f"/api/scans/{scan['id']}/findings", headers=headers)).json()
    assert findings["pagination"]["totalItems"] == 3
    finding = findings["data"][0]
    assert finding["scanId"] == scan["id"]
    assert finding["codeSnippet"] == "eval(x)"
    assert finding["reviewStatus"] == "open"

    high = (await api.client.get("/api/findings?severity=high,critical", headers=headers)).json()
    assert {f["severity"] for f in high["data"]} == {"high", "critical"}
    code = (await api.client.get("/api/findings?category=code", headers=headers)).json()
    assert code["pagination"]["totalItems"] == 3
    labelled = (await api.client.get("/api/findings?category=Code Vulnerability", headers=headers)).json()
    assert labelled["pagination"]["totalItems"] == 3
    bad = await api.client.get("/api/findings?severity=extreme", headers=headers)
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_finding_review_persists(api, tmp_path) -> None:
    headers = await api.register("ada@example.com")
    me = (await api.client.get("/api/users/me", headers=headers)).json()["data"]
    scan = await completed_scan_with_findings(api, tmp_path, headers)
    finding_id = (await api.client.get(f"/api/scans/{scan['id']}/findings", headers=headers)).json()["data"][0]["id"]

    reviewed = await api.client.patch(
        f"/api/findings/{finding_id}",
        json={"reviewStatus": "false_positive", "reviewNote": "  Test fixture, not production code.  "},
        headers=headers,
    )
    assert reviewed.status_code == 200
    data = reviewed.json()["data"]
    assert data["reviewStatus"] == "false_positive"
    assert data["reviewNote"] == "Test fixture, not production code."
    assert data["reviewedBy"] == me["id"] and data["reviewedAt"]

    # Persisted: a fresh read returns the same review.
    fetched = (await api.client.get(f"/api/findings/{finding_id}", headers=headers)).json()["data"]
    assert (fetched["reviewStatus"], fetched["reviewNote"]) == ("false_positive", "Test fixture, not production code.")
    filtered = (await api.client.get("/api/findings?reviewStatus=false_positive", headers=headers)).json()
    assert [f["id"] for f in filtered["data"]] == [finding_id]

    for status in ("acknowledged", "resolved", "open"):
        response = await api.client.patch(f"/api/findings/{finding_id}", json={"reviewStatus": status}, headers=headers)
        assert response.json()["data"]["reviewStatus"] == status
        assert response.json()["data"]["reviewNote"] is None


@pytest.mark.asyncio
async def test_finding_review_validation_and_ownership(api, tmp_path) -> None:
    owner = await api.register("owner@example.com")
    other = await api.register("other@example.com")
    scan = await completed_scan_with_findings(api, tmp_path, owner)
    finding_id = (await api.client.get(f"/api/scans/{scan['id']}/findings", headers=owner)).json()["data"][0]["id"]

    invalid = await api.client.patch(f"/api/findings/{finding_id}", json={"reviewStatus": "ignored"}, headers=owner)
    assert invalid.status_code == 422
    long_note = await api.client.patch(
        f"/api/findings/{finding_id}", json={"reviewStatus": "acknowledged", "reviewNote": "x" * 2001}, headers=owner
    )
    assert long_note.status_code == 422
    foreign = await api.client.patch(f"/api/findings/{finding_id}", json={"reviewStatus": "resolved"}, headers=other)
    assert foreign.status_code == 404
    unchanged = (await api.client.get(f"/api/findings/{finding_id}", headers=owner)).json()["data"]
    assert unchanged["reviewStatus"] == "open"
