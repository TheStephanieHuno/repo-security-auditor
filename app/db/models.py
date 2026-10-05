from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(StrEnum):
    DEVELOPER = "DEVELOPER"
    SECURITY_ANALYST = "SECURITY_ANALYST"
    ADMINISTRATOR = "ADMINISTRATOR"


class ScanStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ScannerName(StrEnum):
    SEMGREP = "SEMGREP"
    GITLEAKS = "GITLEAKS"
    TRIVY = "TRIVY"
    CHECKOV = "CHECKOV"


class ScannerRunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class FindingCategory(StrEnum):
    CODE = "CODE"
    SECRET = "SECRET"
    DEPENDENCY = "DEPENDENCY"
    CONFIGURATION = "CONFIGURATION"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Confidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FindingReviewStatus(StrEnum):
    OPEN = "OPEN"
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"


class EvidenceType(StrEnum):
    CODE = "CODE"
    DEPENDENCY = "DEPENDENCY"
    SECRET = "SECRET"
    CONFIGURATION = "CONFIGURATION"


class ReportStatus(StrEnum):
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class PolicyStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


class ExplanationStatus(StrEnum):
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.DEVELOPER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    scans_requested: Mapped[list["Scan"]] = relationship(back_populates="requester")

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_users_name_non_empty"),
        CheckConstraint(
            "role IN ('DEVELOPER', 'SECURITY_ANALYST', 'ADMINISTRATOR')",
            name="ck_users_role",
        ),
    )


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_private: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="repositories")
    scans: Mapped[list["Scan"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "github_url", name="uq_repositories_owner_github_url"),
    )


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ScanStatus.QUEUED.value)
    target_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    repository: Mapped["Repository"] = relationship(back_populates="scans")
    requester: Mapped["User"] = relationship(back_populates="scans_requested")
    scanner_runs: Mapped[list["ScannerRun"]] = relationship(
        back_populates="scan", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="scan", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED')",
            name="ck_scans_status",
        ),
    )


class ScannerRun(Base):
    __tablename__ = "scanner_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scanner_name: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ScannerRunStatus.QUEUED.value
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finding_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    scan: Mapped["Scan"] = relationship(back_populates="scanner_runs")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scanner_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("scan_id", "scanner_name", name="uq_scanner_runs_scan_scanner"),
        CheckConstraint(
            "scanner_name IN ('SEMGREP', 'GITLEAKS', 'TRIVY', 'CHECKOV')",
            name="ck_scanner_runs_scanner_name",
        ),
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMEOUT')",
            name="ck_scanner_runs_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_scanner_runs_attempt_count"),
        CheckConstraint("finding_count >= 0", name="ck_scanner_runs_finding_count"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scanner_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scanner_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=FindingReviewStatus.OPEN.value, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    scanner_run: Mapped["ScannerRun"] = relationship(back_populates="findings")
    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )
    explanations: Mapped[list["FindingExplanation"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_findings_scanner_run_fingerprint", "scanner_run_id", "fingerprint"),
        CheckConstraint(
            "category IN ('CODE', 'SECRET', 'DEPENDENCY', 'CONFIGURATION')",
            name="ck_findings_category",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_findings_severity",
        ),
        CheckConstraint(
            "confidence IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_findings_confidence",
        ),
        CheckConstraint(
            "review_status IN ('OPEN', 'CONFIRMED', 'DISMISSED')",
            name="ck_findings_review_status",
        ),
        CheckConstraint(
            "line_start IS NULL OR line_start > 0",
            name="ck_findings_line_start_positive",
        ),
        CheckConstraint(
            "line_end IS NULL OR (line_end > 0 AND (line_start IS NULL OR line_end >= line_start))",
            name="ck_findings_line_end_valid",
        ),
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_value_redacted: Mapped[str | None] = mapped_column(String(512), nullable=True)
    context_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_reference: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    finding: Mapped["Finding"] = relationship(back_populates="evidence")

    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('CODE', 'DEPENDENCY', 'SECRET', 'CONFIGURATION')",
            name="ck_evidence_type",
        ),
        CheckConstraint(
            "line_start IS NULL OR line_start > 0",
            name="ck_evidence_line_start_positive",
        ),
        CheckConstraint(
            "line_end IS NULL OR (line_end > 0 AND (line_start IS NULL OR line_end >= line_start))",
            name="ck_evidence_line_end_valid",
        ),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ReportStatus.QUEUED.value)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    total_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    policy_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PolicyStatus.NOT_EVALUATED.value
    )
    report_version: Mapped[str] = mapped_column(String(32), nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    scan: Mapped["Scan"] = relationship(back_populates="report")

    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'GENERATING', 'READY', 'FAILED')",
            name="ck_reports_status",
        ),
        CheckConstraint(
            "policy_status IN ('PASS', 'FAIL', 'NOT_EVALUATED')",
            name="ck_reports_policy_status",
        ),
        CheckConstraint("total_findings >= 0", name="ck_reports_total_findings"),
        CheckConstraint("critical_count >= 0", name="ck_reports_critical_count"),
        CheckConstraint("high_count >= 0", name="ck_reports_high_count"),
        CheckConstraint("medium_count >= 0", name="ck_reports_medium_count"),
        CheckConstraint("low_count >= 0", name="ck_reports_low_count"),
    )


class FindingExplanation(Base):
    __tablename__ = "finding_explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ExplanationStatus.QUEUED.value
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    uncertainty_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_references: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    failure_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    finding: Mapped["Finding"] = relationship(back_populates="explanations")

    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'GENERATING', 'READY', 'FAILED')",
            name="ck_finding_explanations_status",
        ),
    )
