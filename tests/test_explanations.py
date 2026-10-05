from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.explanations import (
    create_queued_explanation,
    mark_explanation_failed,
    mark_explanation_generating,
    mark_explanation_ready,
)
from app.db.models import (
    Base,
    Confidence,
    Evidence,
    EvidenceType,
    Finding,
    FindingCategory,
    ScannerName,
    ScannerRun,
    ScannerRunStatus,
    Severity,
    User,
    Repository,
    Scan,
    ScanStatus,
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


async def create_finding(db: AsyncSession) -> Finding:
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
    scan = Scan(
        repository_id=repository.id,
        requested_by=user.id,
        target_branch="main",
        status=ScanStatus.COMPLETED.value,
    )
    db.add(scan)
    await db.flush()
    scanner_run = ScannerRun(
        scan_id=scan.id,
        scanner_name=ScannerName.SEMGREP.value,
        status=ScannerRunStatus.COMPLETED.value,
    )
    db.add(scanner_run)
    await db.flush()
    finding = Finding(
        scanner_run_id=scanner_run.id,
        category=FindingCategory.CODE.value,
        rule_id="rule-1",
        title="Finding",
        description="Description",
        severity=Severity.HIGH.value,
        confidence=Confidence.HIGH.value,
        recommendation="Fix it",
        fingerprint="fingerprint-1",
    )
    db.add(finding)
    await db.flush()
    return finding


@pytest.mark.asyncio
async def test_explanation_references_only_finding_evidence(db: AsyncSession) -> None:
    finding = await create_finding(db)
    evidence = Evidence(
        finding_id=finding.id,
        evidence_type=EvidenceType.CODE.value,
        file_path="src/app.py",
        line_start=10,
        line_end=10,
        code_snippet="unsafe()",
    )
    db.add(evidence)
    await db.flush()

    explanation = await create_queued_explanation(
        db,
        finding=finding,
        provider="test-provider",
        model_version="model-1",
        input_hash="a" * 64,
        evidence_ids=[evidence.id, evidence.id],
    )

    assert explanation.status == "QUEUED"
    assert explanation.evidence_references == [evidence.id]

    with pytest.raises(ValueError, match="belong to the finding"):
        await create_queued_explanation(
            db,
            finding=finding,
            provider="test-provider",
            model_version="model-1",
            input_hash="b" * 64,
            evidence_ids=[999],
        )


@pytest.mark.asyncio
async def test_explanation_lifecycle_preserves_terminal_states(
    db: AsyncSession,
) -> None:
    finding = await create_finding(db)
    explanation = await create_queued_explanation(
        db,
        finding=finding,
        provider="test-provider",
        model_version="model-1",
        input_hash="a" * 64,
        evidence_ids=[],
    )

    await mark_explanation_generating(db, explanation=explanation)
    await mark_explanation_ready(
        db,
        explanation=explanation,
        explanation_text="Grounded explanation",
        uncertainty_statement="Evidence is limited.",
    )
    await mark_explanation_failed(
        db, explanation=explanation, failure_summary="late failure"
    )

    assert explanation.status == "READY"
    assert explanation.explanation == "Grounded explanation"
    assert explanation.failure_summary is None
