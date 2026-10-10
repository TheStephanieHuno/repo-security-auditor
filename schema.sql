-- ============================================================================
-- REPO SECURITY AUDITOR — PRODUCTION DATABASE DDL (PostgreSQL 16)
-- Implements Database Design Specification (DDS) v1.0
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS findings CASCADE;
DROP TABLE IF EXISTS scans CASCADE;
DROP TABLE IF EXISTS repositories CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 1. users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'developer',
    on_scan_completion BOOLEAN NOT NULL DEFAULT TRUE,
    on_scan_failure BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_users_role CHECK (role IN ('developer', 'security_analyst', 'administrator'))
);

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

-- 2. repositories
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url VARCHAR(1024) NOT NULL,
    name VARCHAR(255) NOT NULL,
    owner VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'github',
    default_branch VARCHAR(255) NOT NULL DEFAULT 'main',
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    added_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_repositories_added_by FOREIGN KEY (added_by) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_repository_url UNIQUE (added_by, url)
);

CREATE TRIGGER trg_repositories_updated_at
BEFORE UPDATE ON repositories
FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

-- 3. scans
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id UUID NOT NULL,
    initiated_by UUID NOT NULL,
    branch VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_scans_repository FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
    CONSTRAINT fk_scans_initiated_by FOREIGN KEY (initiated_by) REFERENCES users(id),
    CONSTRAINT chk_scans_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT chk_scans_progress CHECK (progress >= 0 AND progress <= 100)
);

CREATE TRIGGER trg_scans_updated_at
BEFORE UPDATE ON scans
FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

-- 4. findings
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL,
    repository_id UUID NOT NULL,
    severity VARCHAR(50) NOT NULL,
    confidence VARCHAR(50) NOT NULL DEFAULT 'high',
    category VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    code_snippet TEXT,
    recommendation TEXT NOT NULL,
    ai_explanation TEXT,
    review_status VARCHAR(50) NOT NULL DEFAULT 'open',
    review_note TEXT,
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_findings_scan FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE,
    CONSTRAINT fk_findings_repository FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
    CONSTRAINT fk_findings_reviewed_by FOREIGN KEY (reviewed_by) REFERENCES users(id),
    CONSTRAINT chk_findings_severity CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    CONSTRAINT chk_findings_confidence CHECK (confidence IN ('high', 'medium', 'low')),
    CONSTRAINT chk_findings_review_status CHECK (review_status IN ('open', 'acknowledged', 'false_positive', 'resolved'))
);

-- 5. reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'generating',
    format VARCHAR(10) NOT NULL DEFAULT 'pdf',
    file_url VARCHAR(1024),
    file_size INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT fk_reports_scan FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE,
    CONSTRAINT chk_reports_status CHECK (status IN ('generating', 'ready', 'failed'))
);

-- Indexes
CREATE UNIQUE INDEX idx_users_email_lower ON users (LOWER(email));
CREATE INDEX idx_repositories_added_by ON repositories (added_by);
CREATE INDEX idx_scans_repository_id ON scans (repository_id);
CREATE INDEX idx_scans_status ON scans (status);
CREATE INDEX idx_findings_scan_id ON findings (scan_id);
CREATE INDEX idx_findings_repository_id ON findings (repository_id);
CREATE INDEX idx_findings_severity ON findings (severity);
CREATE INDEX idx_findings_review_status ON findings (review_status);
CREATE INDEX idx_reports_scan_id ON reports (scan_id);