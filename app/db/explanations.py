import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Evidence, ExplanationStatus, Finding, FindingExplanation

_INPUT_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_text(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def _validate_input_hash(input_hash: str) -> str:
    if not _INPUT_HASH_PATTERN.fullmatch(input_hash):
        raise ValueError("input_hash must be a lowercase SHA-256 hex digest")
    return input_hash


async def validate_evidence_references(
    db: AsyncSession, *, finding_id: int, evidence_ids: list[int]
) -> list[int]:
    references = list(dict.fromkeys(evidence_ids))
    if any(evidence_id <= 0 for evidence_id in references):
        raise ValueError("evidence references must be positive IDs")

    if not references:
        return []

    result = await db.execute(
        select(Evidence.id).where(
            Evidence.finding_id == finding_id,
            Evidence.id.in_(references),
        )
    )
    valid_ids = set(result.scalars().all())
    if valid_ids != set(references):
        raise ValueError("evidence references must belong to the finding")
    return references


async def create_queued_explanation(
    db: AsyncSession,
    *,
    finding: Finding,
    provider: str,
    model_version: str,
    input_hash: str,
    evidence_ids: list[int],
) -> FindingExplanation:
    references = await validate_evidence_references(
        db, finding_id=finding.id, evidence_ids=evidence_ids
    )
    explanation = FindingExplanation(
        finding_id=finding.id,
        status=ExplanationStatus.QUEUED.value,
        provider=_require_text(provider, "provider"),
        model_version=_require_text(model_version, "model_version"),
        evidence_references=references,
        input_hash=_validate_input_hash(input_hash),
    )
    db.add(explanation)
    await db.flush()
    return explanation


async def mark_explanation_generating(
    db: AsyncSession, *, explanation: FindingExplanation
) -> None:
    if explanation.status != ExplanationStatus.QUEUED.value:
        return
    explanation.status = ExplanationStatus.GENERATING.value
    await db.flush()


async def mark_explanation_ready(
    db: AsyncSession,
    *,
    explanation: FindingExplanation,
    explanation_text: str,
    impact_summary: str | None = None,
    remediation_guidance: str | None = None,
    uncertainty_statement: str | None = None,
) -> None:
    if explanation.status in {
        ExplanationStatus.READY.value,
        ExplanationStatus.FAILED.value,
    }:
        return
    explanation.explanation = _require_text(explanation_text, "explanation")
    explanation.impact_summary = impact_summary
    explanation.remediation_guidance = remediation_guidance
    explanation.uncertainty_statement = uncertainty_statement
    explanation.failure_summary = None
    explanation.status = ExplanationStatus.READY.value
    await db.flush()


async def mark_explanation_failed(
    db: AsyncSession, *, explanation: FindingExplanation, failure_summary: str
) -> None:
    if explanation.status in {
        ExplanationStatus.READY.value,
        ExplanationStatus.FAILED.value,
    }:
        return
    explanation.failure_summary = _require_text(failure_summary, "failure_summary")
    explanation.status = ExplanationStatus.FAILED.value
    await db.flush()
