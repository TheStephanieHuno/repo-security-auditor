"""
SQLAlchemy 2.0 Async ORM Models — Repo Security Auditor
Implements Database Design Specification (DDS) v1.0.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Uuid,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend_app_test.db.session import Base


def utcnow() -> datetime:
    """Returns the current UTC datetime with explicit timezone info."""
    return datetime.now(timezone.utc)


class User(Base):
    """
    Table: users
    Stores user credentials, roles, and notification preferences.
    """
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('developer', 'security_analyst', 'administrator')", name="chk_users_role"),
        Index("idx_users_email_lower", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="developer", nullable=False)
    on_scan_completion: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    on_scan_failure: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # 1:N Relationships with Cascade Delete
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    scans: Mapped[list["Scan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class Repository(Base):
    """
    Table: repositories
    Stores tracked GitHub repositories added by authenticated users.
    """
    __tablename__ = "repositories"
    __table_args__ = (
        CheckConstraint("provider IN ('github', 'gitlab', 'bitbucket')", name="chk_repositories_provider"),
        UniqueConstraint("added_by", "url", name="uq_user_repository_url"),
        Index("idx_repositories_added_by", "added_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="github", nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="repositories")
    scans: Mapped[list["Scan"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class Scan(Base):
    """
    Table: scans
    Tracks scan lifecycle states, progress, and execution timestamps.
    """
    __tablename__ = "scans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="chk_scans_status"
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="chk_scans_progress"),
        Index("idx_scans_repository_id", "repository_id"),
        Index("idx_scans_status", "status"),
        Index("idx_scans_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    initiated_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="scans")
    user: Mapped["User"] = relationship(back_populates="scans")
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class Finding(Base):
    """
    Table: findings
    Stores normalized security findings identified across all 4 scanners.
    """
    __tablename__ = "findings"
    __table_args__ = (
        CheckConstraint("severity IN ('critical', 'high', 'medium', 'low', 'info')", name="chk_findings_severity"),
        CheckConstraint("confidence IN ('high', 'medium', 'low')", name="chk_findings_confidence"),
        CheckConstraint(
            "review_status IN ('open', 'acknowledged', 'false_positive', 'resolved')",
            name="chk_findings_review_status"
        ),
        Index("idx_findings_scan_id", "scan_id"),
        Index("idx_findings_repository_id", "repository_id"),
        Index("idx_findings_severity", "severity"),
        Index("idx_findings_confidence", "confidence"),
        Index("idx_findings_review_status", "review_status"),
        Index("idx_findings_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    repository_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), default="high", nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    scan: Mapped["Scan"] = relationship(back_populates="findings")
    repository: Mapped["Repository"] = relationship(back_populates="findings")


class Report(Base):
    """
    Table: reports
    Maintains compilation status and binary file pointers for PDF security reports.
    """
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("status IN ('generating', 'ready', 'failed')", name="chk_reports_status"),
        CheckConstraint("format IN ('pdf', 'json', 'csv')", name="chk_reports_format"),
        Index("idx_reports_scan_id", "scan_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="generating", nullable=False)
    format: Mapped[str] = mapped_column(String(10), default="pdf", nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    scan: Mapped["Scan"] = relationship(back_populates="reports")