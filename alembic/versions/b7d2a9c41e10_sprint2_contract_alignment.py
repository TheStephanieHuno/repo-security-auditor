"""align persistence with the sprint 2 contract

Adds OSV/CONFIG scanners, CANCELLED scan and scanner-run states, the
open/acknowledged/false_positive/resolved review vocabulary with review
metadata, public UUID identifiers, and the revoked-token denylist.

Revision ID: b7d2a9c41e10
Revises: 6e5685c45f9c
Create Date: 2026-10-06 10:00:00.000000
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2a9c41e10"
down_revision: Union[str, Sequence[str], None] = "6e5685c45f9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PUBLIC_ID_TABLES = ("users", "repositories", "scans", "findings", "reports")

SCAN_STATUSES_OLD = "('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED')"
SCAN_STATUSES_NEW = "('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED')"
SCANNERS_OLD = "('SEMGREP', 'GITLEAKS', 'TRIVY', 'CHECKOV')"
SCANNERS_NEW = "('SEMGREP', 'GITLEAKS', 'TRIVY', 'CHECKOV', 'OSV', 'CONFIG')"
RUN_STATUSES_OLD = "('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMEOUT')"
RUN_STATUSES_NEW = "('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED')"
REVIEW_OLD = "('OPEN', 'CONFIRMED', 'DISMISSED')"
REVIEW_NEW = "('OPEN', 'ACKNOWLEDGED', 'FALSE_POSITIVE', 'RESOLVED')"


def _replace_check(table: str, name: str, condition: str) -> None:
    with op.batch_alter_table(table, recreate="always") as batch:
        batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, sa.text(condition))


def _add_public_ids() -> None:
    connection = op.get_bind()
    for table in PUBLIC_ID_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("public_id", sa.Uuid(), nullable=True))
        rows = connection.execute(sa.text(f"SELECT id FROM {table}")).scalars().all()
        public_id = sa.table(table, sa.column("id"), sa.column("public_id", sa.Uuid()))
        for row_id in rows:
            connection.execute(
                public_id.update()
                .where(public_id.c.id == row_id)
                .values(public_id=uuid.uuid4())
            )
        with op.batch_alter_table(table) as batch:
            batch.alter_column("public_id", existing_type=sa.Uuid(), nullable=False)
            batch.create_index(f"ix_{table}_public_id", ["public_id"], unique=True)


def upgrade() -> None:
    _add_public_ids()

    with op.batch_alter_table("scans") as batch:
        batch.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    _replace_check("scans", "ck_scans_status", f"status IN {SCAN_STATUSES_NEW}")

    _replace_check(
        "scanner_runs", "ck_scanner_runs_scanner_name", f"scanner_name IN {SCANNERS_NEW}"
    )
    _replace_check("scanner_runs", "ck_scanner_runs_status", f"status IN {RUN_STATUSES_NEW}")

    with op.batch_alter_table("findings", recreate="always") as batch:
        batch.drop_constraint("ck_findings_review_status", type_="check")
        batch.add_column(sa.Column("review_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column("reviewed_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_findings_reviewed_by_users", "users", ["reviewed_by"], ["id"], ondelete="SET NULL"
        )
    op.execute("UPDATE findings SET review_status = 'ACKNOWLEDGED' WHERE review_status = 'CONFIRMED'")
    op.execute("UPDATE findings SET review_status = 'FALSE_POSITIVE' WHERE review_status = 'DISMISSED'")
    with op.batch_alter_table("findings") as batch:
        batch.create_check_constraint(
            "ck_findings_review_status", sa.text(f"review_status IN {REVIEW_NEW}")
        )

    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")

    with op.batch_alter_table("findings", recreate="always") as batch:
        batch.drop_constraint("ck_findings_review_status", type_="check")
    op.execute(
        "UPDATE findings SET review_status = 'CONFIRMED' "
        "WHERE review_status IN ('ACKNOWLEDGED', 'RESOLVED')"
    )
    op.execute("UPDATE findings SET review_status = 'DISMISSED' WHERE review_status = 'FALSE_POSITIVE'")
    with op.batch_alter_table("findings", recreate="always") as batch:
        batch.drop_constraint("fk_findings_reviewed_by_users", type_="foreignkey")
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by")
        batch.drop_column("review_note")
        batch.create_check_constraint(
            "ck_findings_review_status", sa.text(f"review_status IN {REVIEW_OLD}")
        )

    op.execute("UPDATE scanner_runs SET status = 'FAILED' WHERE status = 'CANCELLED'")
    op.execute("DELETE FROM scanner_runs WHERE scanner_name IN ('OSV', 'CONFIG')")
    _replace_check("scanner_runs", "ck_scanner_runs_status", f"status IN {RUN_STATUSES_OLD}")
    _replace_check(
        "scanner_runs", "ck_scanner_runs_scanner_name", f"scanner_name IN {SCANNERS_OLD}"
    )

    op.execute("UPDATE scans SET status = 'FAILED' WHERE status = 'CANCELLED'")
    _replace_check("scans", "ck_scans_status", f"status IN {SCAN_STATUSES_OLD}")
    with op.batch_alter_table("scans") as batch:
        batch.drop_column("cancelled_at")

    for table in reversed(PUBLIC_ID_TABLES):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_public_id")
            batch.drop_column("public_id")
