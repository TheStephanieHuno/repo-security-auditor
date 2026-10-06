from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Confidence,
    Evidence,
    EvidenceType,
    Finding,
    FindingCategory,
    FindingReviewStatus,
    ScannerRun,
    Severity,
)

MAX_TEXT_LENGTH = 4000
MAX_SNIPPET_LINES = 20
MAX_SNIPPET_LENGTH = 2000

_SECRET_PATTERNS = (
    re.compile(r"(?i)(AKIA[0-9A-Z]{16})"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(password\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(secret\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"-----BEGIN [^-]+ PRIVATE KEY-----.*?-----END [^-]+ PRIVATE KEY-----"),
)

_SEVERITY_MAP: dict[str, dict[str, Severity]] = {
    "SEMGREP": {
        "INFO": Severity.LOW,
        "WARNING": Severity.MEDIUM,
        "ERROR": Severity.HIGH,
        "BLOCKER": Severity.CRITICAL,
    },
    "GITLEAKS": {value: Severity(value) for value in ("LOW", "MEDIUM", "HIGH", "CRITICAL")},
    "TRIVY": {
        "UNKNOWN": Severity.LOW,
        "LOW": Severity.LOW,
        "MEDIUM": Severity.MEDIUM,
        "HIGH": Severity.HIGH,
        "CRITICAL": Severity.CRITICAL,
    },
    "CHECKOV": {value: Severity(value) for value in ("LOW", "MEDIUM", "HIGH", "CRITICAL")},
    "OSV": {
        "LOW": Severity.LOW,
        "MODERATE": Severity.MEDIUM,
        "MEDIUM": Severity.MEDIUM,
        "HIGH": Severity.HIGH,
        "CRITICAL": Severity.CRITICAL,
    },
    "CONFIG": {value: Severity(value) for value in ("LOW", "MEDIUM", "HIGH", "CRITICAL")},
}


@dataclass(frozen=True)
class NormalizedEvidence:
    evidence_type: EvidenceType
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    matched_value_redacted: str | None = None
    context_hash: str | None = None
    raw_reference: str | None = None


@dataclass(frozen=True)
class NormalizedFinding:
    category: FindingCategory
    source_scanner: str
    rule_id: str
    title: str
    description: str
    severity: Severity
    confidence: Confidence
    recommendation: str
    fingerprint: str
    file_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    evidence: tuple[NormalizedEvidence, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id must not be empty")
        for name, value in (
            ("title", self.title),
            ("description", self.description),
            ("recommendation", self.recommendation),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
            if len(value) > MAX_TEXT_LENGTH:
                raise ValueError(f"{name} exceeds the maximum length")
        if self.line_start is not None and self.line_start <= 0:
            raise ValueError("line_start must be positive")
        if self.line_end is not None and (
            self.line_end <= 0
            or (self.line_start is not None and self.line_end < self.line_start)
        ):
            raise ValueError("line_end must be valid")


def map_severity(source_scanner: str, raw_severity: str | None) -> tuple[Severity, str | None]:
    scanner = source_scanner.upper()
    if scanner not in _SEVERITY_MAP:
        raise ValueError(f"unsupported scanner: {source_scanner}")
    normalized = (raw_severity or "UNKNOWN").upper()
    severity = _SEVERITY_MAP[scanner].get(normalized)
    if severity is None:
        return Severity.MEDIUM, "unknown severity mapped to MEDIUM"
    if normalized == "UNKNOWN" and scanner != "TRIVY":
        return Severity.MEDIUM, "unknown severity mapped to MEDIUM"
    if normalized == "UNKNOWN":
        return Severity.LOW, "unknown severity mapped to LOW"
    return severity, None


def normalize_repository_path(path: str | None) -> str | None:
    if path is None:
        return None
    value = path.replace("\\", "/").strip()
    if not value:
        return None
    if PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute():
        raise ValueError("absolute paths are not allowed")
    normalized = PurePosixPath(value)
    if ".." in normalized.parts:
        raise ValueError("paths must not escape the repository")
    return str(normalized)


def redact_sensitive_text(value: str | None, *, max_length: int = MAX_SNIPPET_LENGTH) -> str | None:
    if value is None:
        return None
    redacted = value
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            redacted = pattern.sub(
                lambda match: (
                    f"{match.group(1)[:4]}{'*' * max(8, len(match.group(0)) - 4)}"
                    if match.group(1) == match.group(0)
                    else f"{match.group(1)}{'*' * max(8, len(match.group(0)) - len(match.group(1)))}"
                ),
                redacted,
            )
        else:
            redacted = pattern.sub("[REDACTED PRIVATE KEY]", redacted)
    lines = redacted.splitlines()[:MAX_SNIPPET_LINES]
    return "\n".join(lines)[:max_length]


def build_fingerprint(
    *,
    source_scanner: str,
    rule_id: str,
    category: FindingCategory,
    file_path: str | None,
    line_start: int | None,
    stable_resource: str | None,
    title: str,
) -> str:
    parts = (
        source_scanner.upper(),
        rule_id.strip(),
        category.value,
        file_path or "",
        str(line_start or ""),
        stable_resource or "",
        " ".join(title.lower().split()),
    )
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def collapse_duplicates(findings: list[NormalizedFinding]) -> list[NormalizedFinding]:
    unique: dict[str, NormalizedFinding] = {}
    for finding in findings:
        unique.setdefault(finding.fingerprint, finding)
    return list(unique.values())


async def persist_normalized_findings(
    db: AsyncSession,
    *,
    scanner_run: ScannerRun,
    findings: list[NormalizedFinding],
) -> list[Finding]:
    existing = await db.execute(
        select(Finding.fingerprint).where(Finding.scanner_run_id == scanner_run.id)
    )
    existing_fingerprints = set(existing.scalars().all())

    # Build every row before adding any, so a validation error leaves no partial findings.
    persisted: list[Finding] = []
    for normalized in collapse_duplicates(findings):
        if normalized.fingerprint in existing_fingerprints:
            continue
        safe_path = normalize_repository_path(normalized.file_path)
        finding = Finding(
            scanner_run_id=scanner_run.id,
            category=normalized.category.value,
            rule_id=normalized.rule_id[:255],
            title=redact_sensitive_text(normalized.title, max_length=500) or "",
            description=redact_sensitive_text(normalized.description) or "",
            severity=normalized.severity.value,
            confidence=normalized.confidence.value,
            recommendation=redact_sensitive_text(normalized.recommendation) or "",
            file_path=safe_path,
            line_start=normalized.line_start,
            line_end=normalized.line_end,
            fingerprint=normalized.fingerprint,
            review_status=FindingReviewStatus.OPEN.value,
        )
        for evidence in normalized.evidence:
            finding.evidence.append(
                Evidence(
                    evidence_type=evidence.evidence_type.value,
                    file_path=normalize_repository_path(evidence.file_path),
                    line_start=evidence.line_start,
                    line_end=evidence.line_end,
                    code_snippet=redact_sensitive_text(evidence.code_snippet),
                    matched_value_redacted=redact_sensitive_text(
                        evidence.matched_value_redacted, max_length=512
                    ),
                    context_hash=evidence.context_hash,
                    raw_reference=redact_sensitive_text(
                        evidence.raw_reference, max_length=1024
                    ),
                )
            )
        persisted.append(finding)
    db.add_all(persisted)
    await db.flush()
    scanner_run.finding_count = len(existing_fingerprints) + len(persisted)
    await db.flush()
    return persisted
