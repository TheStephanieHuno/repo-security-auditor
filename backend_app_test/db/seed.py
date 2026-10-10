"""
Database Seeder Script — Populates realistic test data into PostgreSQL.
"""

import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from backend_app_test.db.session import AsyncSessionLocal, engine, Base
from backend_app_test.db.models import User, Repository, Scan, Finding, Report
from backend_app_test.core.security import hash_password


async def seed_data():
    print("Seeding PostgreSQL with realistic test data...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing = await db.execute(select(User).where(User.email == "developer@example.com"))
        if existing.scalar_one_or_none():
            print("Database already contains seed data. Skipping.")
            return

        now = datetime.now(timezone.utc)

        # 1. Seed Users
        dev_user = User(
            id=uuid.uuid4(),
            name="Alex Developer",
            email="developer@example.com",
            hashed_password=hash_password("DevPassword123!"),
            role="developer",
            on_scan_completion=True,
            on_scan_failure=True,
            is_verified=True,
            created_at=now,
            updated_at=now
        )
        analyst_user = User(
            id=uuid.uuid4(),
            name="Sarah Analyst",
            email="analyst@example.com",
            hashed_password=hash_password("AnalystPassword123!"),
            role="security_analyst",
            on_scan_completion=True,
            on_scan_failure=True,
            is_verified=True,
            created_at=now,
            updated_at=now
        )
        db.add(dev_user)
        db.add(analyst_user)
        await db.flush()

        # 2. Seed Repository
        repo = Repository(
            id=uuid.uuid4(),
            url="https://github.com/organization/core-payment-api",
            name="core-payment-api",
            owner="organization",
            provider="github",
            default_branch="main",
            is_valid=True,
            added_by=dev_user.id,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2)
        )
        db.add(repo)
        await db.flush()

        # 3. Seed Scan
        scan = Scan(
            id=uuid.uuid4(),
            repository_id=repo.id,
            initiated_by=dev_user.id,
            branch="main",
            status="completed",
            progress=100,
            started_at=now - timedelta(minutes=15),
            completed_at=now - timedelta(minutes=10),
            cancelled_at=None,
            created_at=now - timedelta(minutes=15),
            updated_at=now - timedelta(minutes=10)
        )
        db.add(scan)
        await db.flush()

        # 4. Seed Findings across all 4 scanners
        findings = [
            # Secret Scanner finding
            Finding(
                id=uuid.uuid4(),
                scan_id=scan.id,
                repository_id=repo.id,
                severity="critical",
                confidence="high",
                category="Secret Exposure",
                title="Hardcoded AWS Secret Access Key",
                description="An active AWS secret access key was detected in configuration code.",
                file_path="src/config/aws.ts",
                line_start=14,
                line_end=14,
                code_snippet="const AWS_KEY = 'AKIAIOSFODNN7EXAMPLE';",
                recommendation="Rotate this AWS key immediately in AWS IAM and use environment variables.",
                ai_explanation="The key was committed in plain text. Provides unrestricted AWS infrastructure access.",
                review_status="open",
                created_at=now - timedelta(minutes=10)
            ),
            # Code Scanner finding (Semgrep)
            Finding(
                id=uuid.uuid4(),
                scan_id=scan.id,
                repository_id=repo.id,
                severity="high",
                confidence="high",
                category="Source Code Vulnerability",
                title="SQL Injection in Authentication Query",
                description="Raw user input concatenated directly into SQL query string.",
                file_path="src/services/auth.py",
                line_start=42,
                line_end=45,
                code_snippet="query = f'SELECT * FROM users WHERE email = \\'{email}\\''",
                recommendation="Use parameterized queries or SQLAlchemy ORM query builders.",
                ai_explanation="Allows SQL injection, enabling authentication bypass.",
                review_status="acknowledged",
                review_note="Scheduled for remediation.",
                reviewed_by=analyst_user.id,
                reviewed_at=now - timedelta(minutes=5),
                created_at=now - timedelta(minutes=10)
            ),
            # Dependency Scanner finding (OSV)
            Finding(
                id=uuid.uuid4(),
                scan_id=scan.id,
                repository_id=repo.id,
                severity="high",
                confidence="high",
                category="Dependency Vulnerability",
                title="urllib3@1.26.4: CVE-2021-33503",
                description="Catastrophic backtracking in URL parsing leads to Denial of Service.",
                file_path="requirements.txt",
                line_start=8,
                line_end=8,
                code_snippet='"urllib3": "1.26.4"',
                recommendation="Upgrade urllib3 to version 1.26.5 or higher.",
                ai_explanation="Vulnerable package allows remote attackers to cause high CPU denial-of-service via crafted URLs.",
                review_status="open",
                created_at=now - timedelta(minutes=10)
            ),
            # Config Scanner finding
            Finding(
                id=uuid.uuid4(),
                scan_id=scan.id,
                repository_id=repo.id,
                severity="critical",
                confidence="high",
                category="Insecure Configuration",
                title="Committed Environment Secrets File",
                description="Production environment file '.env.production' is committed to version control.",
                file_path=".env.production",
                line_start=1,
                line_end=1,
                code_snippet="# Environment file: .env.production",
                recommendation="Purge this file from Git history and append '.env*' to your .gitignore.",
                ai_explanation="Committing environment files exposes database connection strings and cryptographic signing secrets.",
                review_status="open",
                created_at=now - timedelta(minutes=10)
            )
        ]
        for f in findings:
            db.add(f)
        await db.flush()

        # 5. Seed Report
        report = Report(
            id=uuid.uuid4(),
            scan_id=scan.id,
            status="ready",
            format="pdf",
            file_url="/api/reports/sample/pdf",
            file_size=245892,
            created_at=now - timedelta(minutes=9),
            completed_at=now - timedelta(minutes=8)
        )
        db.add(report)

        await db.commit()
        print("PostgreSQL seeded successfully with 2 users, 1 repo, 1 scan, 4 findings, and 1 report!")


if __name__ == "__main__":
    asyncio.run(seed_data())