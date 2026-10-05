from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    Confidence,
    Evidence,
    EvidenceType,
    FindingCategory,
    Repository,
    Scan,
    ScannerName,
    ScannerRun,
    User,
)
from app.db.normalization import (
    NormalizedEvidence,
    NormalizedFinding,
    build_fingerprint,
    collapse_duplicates,
    map_severity,
    normalize_repository_path,
    persist_normalized_findings,
    redact_sensitive_text,
)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def make_finding(*, fingerprint: str = "fingerprint") -> NormalizedFinding:
    return NormalizedFinding(
        category=FindingCategory.SECRET,
        source_scanner=ScannerName.GITLEAKS.value,
        rule_id="aws-access-key",
        title="Exposed cloud access key",
        description="A credential-like value was detected.",
        severity=map_severity("GITLEAKS", "CRITICAL")[0],
        confidence=Confidence.HIGH,
        recommendation="Revoke the credential and use a secret manager.",
        fingerprint=fingerprint,
        file_path="config/settings.py",
        line_start=42,
        line_end=42,
        evidence=(
            NormalizedEvidence(
                evidence_type=EvidenceType.SECRET,
                file_path="config/settings.py",
                line_start=42,
                line_end=42,
                code_snippet='AWS_ACCESS_KEY_ID = "AKIA1234567890ABCDEF"',
                matched_value_redacted="AKIA1234567890ABCDEF",
                raw_reference="gitleaks-result-1",
            ),
        ),
    )


def test_redaction_and_path_validation() -> None:
    redacted = redact_sensitive_text('AWS_KEY="AKIA1234567890ABCDEF"')
    assert redacted is not None
    assert "AKIA1234567890ABCDEF" not in redacted
    assert normalize_repository_path(r"src\config.py") == "src/config.py"
    with pytest.raises(ValueError):
        normalize_repository_path("../outside.txt")
    with pytest.raises(ValueError):
        normalize_repository_path(r"C:\secrets.txt")


def test_severity_mapping_and_safe_fingerprint() -> None:
    severity, warning = map_severity("SEMGREP", "ERROR")
    assert severity.value == "HIGH"
    assert warning is None
    severity, warning = map_severity("TRIVY", "UNKNOWN")
    assert severity.value == "LOW"
    assert warning is not None
    fingerprint = build_fingerprint(
        source_scanner="GITLEAKS",
        rule_id="aws-access-key",
        category=FindingCategory.SECRET,
        file_path="config/settings.py",
        line_start=42,
        stable_resource=None,
        title="Exposed cloud access key",
    )
    assert len(fingerprint) == 64
    assert "AKIA" not in fingerprint


def test_duplicate_findings_are_collapsed() -> None:
    assert len(collapse_duplicates([make_finding(), make_finding()])) == 1


@pytest.mark.asyncio
async def test_normalized_findings_and_evidence_are_persisted_safely(
    db: AsyncSession,
) -> None:
    user = User(name="Owner", email="owner@example.com", password_hash="hash")
    db.add(user)
    await db.flush()
    repository = Repository(
        name="repo",
        github_url="https://github.com/example/repo",
        owner_id=user.id,
    )
    db.add(repository)
    await db.flush()
    scan = Scan(repository_id=repository.id, requested_by=user.id, target_branch="main")
    db.add(scan)
    await db.flush()
    scanner_run = ScannerRun(
        scan_id=scan.id,
        scanner_name=ScannerName.GITLEAKS.value,
    )
    db.add(scanner_run)
    await db.flush()

    persisted = await persist_normalized_findings(
        db,
        scanner_run=scanner_run,
        findings=[make_finding(), make_finding()],
    )
    await db.commit()

    assert len(persisted) == 1
    assert scanner_run.finding_count == 1
    evidence = (
        await db.execute(select(Evidence).where(Evidence.finding_id == persisted[0].id))
    ).scalar_one()
    assert evidence.code_snippet is not None
    assert "AKIA1234567890ABCDEF" not in evidence.code_snippet
