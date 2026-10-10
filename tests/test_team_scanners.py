"""Unit tests for the team backend scanners (backend_app_test.services.scanner).

Offline: no git, Semgrep, or network. Backlog references: US-09 (secrets),
US-11 (dependencies), US-12 (configuration).
"""

import asyncio
import json
from pathlib import Path

from backend_app_test.services.scanner.config_scanner import ConfigScanner
from backend_app_test.services.scanner.dependency_scanner import (
    cvss3_base_score,
    discover_dependencies,
    osv_severity,
    to_findings,
)
from backend_app_test.services.scanner.secret_scanner import SecretScanner

AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLQ"
GITHUB_TOKEN = "ghp_" + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7bC0eF3hJ6"


def run(scanner, path: Path):
    return asyncio.run(scanner.run(str(path)))


# ------------------------------------------------------------- US-09 secrets


def test_secret_scanner_finds_keys_and_never_stores_them(tmp_path: Path) -> None:
    (tmp_path / "config.py").write_text(f'AWS_KEY = "{AWS_KEY}"\nTOKEN = "{GITHUB_TOKEN}"\n')
    findings = run(SecretScanner(), tmp_path)
    assert {f["title"] for f in findings} == {
        "Hardcoded AWS Access Key", "Hardcoded GitHub Personal Access Token",
    }
    for finding in findings:
        assert finding["severity"] in ("critical", "high") and finding["confidence"] == "high"
        assert AWS_KEY not in finding["codeSnippet"] and GITHUB_TOKEN not in finding["codeSnippet"]
        assert "********" in finding["codeSnippet"]


def test_secret_scanner_reads_key_files_and_env_variants(tmp_path: Path) -> None:
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "server.key").write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n")
    (tmp_path / "id_rsa").write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nb3Blbn...\n")
    (tmp_path / ".env.local").write_text(f"AWS={AWS_KEY}\n")
    files = {f["filePath"] for f in run(SecretScanner(), tmp_path)}
    assert files == {"artifacts/server.key", "id_rsa", ".env.local"}


def test_secret_scanner_ignores_lockfile_integrity_hashes(tmp_path: Path) -> None:
    # Base64 integrity hashes contain AKIA-like runs (previously matched case-insensitively).
    (tmp_path / "package-lock.json").write_text(
        '{"integrity": "sha512-x8AKIAqwertyuiopasdfgAKIAIOSFODNN7EXAMPLEzz9akiaabcdefghijklmnop=="}\n'
    )
    assert run(SecretScanner(), tmp_path) == []


# -------------------------------------------------------- US-12 configuration


def test_config_scanner_meets_us12(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATABASE_PASSWORD=s3cr3t-value\nAPI_KEY=abc\n")
    (tmp_path / ".env.production").write_text("SECRET=x\n")
    (tmp_path / ".env.example").write_text("DATABASE_PASSWORD=\n")
    (tmp_path / "settings.py").write_text("DEBUG = True\n")
    (tmp_path / "main.py").write_text(
        "app.add_middleware(\n    CORSMiddleware,\n    allow_origins=['*'],\n    allow_credentials=True,\n)\n"
        "app.run(debug=True)\n"
    )
    (tmp_path / "server.js").write_text("app.use(cors({ origin: '*' }))\n")
    (tmp_path / "safe.py").write_text("app.add_middleware(CORSMiddleware, allow_origins=['https://app.example.com'])\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.py").write_text("DEBUG = True\n")

    findings = run(ConfigScanner(), tmp_path)
    by_file = {}
    for finding in findings:
        by_file.setdefault(finding["filePath"], []).append(finding)

    env = by_file[".env"][0]
    assert env["severity"] == "critical"  # committed env files are critical (US-12)
    assert "DATABASE_PASSWORD" in env["codeSnippet"] and "s3cr3t-value" not in json.dumps(findings)
    assert by_file[".env.production"][0]["severity"] == "critical"
    assert ".env.example" not in by_file
    assert by_file["settings.py"][0]["title"] == "Debug Mode Enabled (DEBUG=True)"
    main_titles = {f["title"]: f["severity"] for f in by_file["main.py"]}
    assert main_titles["Permissive CORS Policy (Wildcard Origin)"] == "critical"  # credentials too
    assert main_titles["Flask Debug Mode Enabled"] == "high"
    assert by_file["server.js"][0]["severity"] == "high"
    assert "safe.py" not in by_file and "node_modules/x.py" not in by_file
    assert all(f["recommendation"] for f in findings)


# ---------------------------------------------------------- US-11 dependencies


def test_dependency_discovery_reads_npm_and_pip_manifests(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps(
        {"dependencies": {"lodash": "4.17.15", "express": "^4.17.1", "x": "latest"}}, indent=2
    ))
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "requirements.txt").write_text("Django==3.2.0\nflask>=2.0\n")
    (tmp_path / "node_modules" / "dep").mkdir(parents=True)
    (tmp_path / "node_modules" / "dep" / "package.json").write_text('{"dependencies": {"y": "1.0.0"}}')

    deps = {(d[0], d[1], d[2], d[3], d[5]) for d in discover_dependencies(str(tmp_path))}
    assert deps == {
        ("npm", "lodash", "4.17.15", "package.json", True),
        ("npm", "express", "4.17.1", "package.json", False),
        ("PyPI", "django", "3.2.0", "api/requirements.txt", True),
    }


def test_dependency_findings_use_real_severity_and_dedupe_aliases() -> None:
    dep = ("npm", "lodash", "4.17.15", "package.json", 5, True)
    ghsa = {
        "id": "GHSA-aaaa-bbbb-cccc", "aliases": ["CVE-2020-8203"], "summary": "Prototype pollution",
        "database_specific": {"severity": "HIGH"},
        "affected": [{"package": {"name": "lodash"}, "ranges": [{"events": [{"fixed": "4.17.19"}]}]}],
    }
    duplicate = {"id": "CVE-2020-8203", "summary": "same advisory"}
    cvss_only = {
        "id": "GHSA-dddd-eeee-ffff", "summary": "Command injection",
        "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}],
    }
    findings = to_findings(dep, [duplicate, ghsa, cvss_only])
    assert len(findings) == 2
    first, second = findings
    assert first["severity"] == "high" and "CVE-2020-8203" in first["description"]
    assert first["recommendation"] == "Upgrade lodash to 4.17.19 or later."
    assert first["category"] == "Dependency Vulnerability" and first["lineStart"] == 5
    assert second["severity"] == "critical"


def test_osv_severity_mapping_and_cvss() -> None:
    assert osv_severity({"database_specific": {"severity": "MODERATE"}}) == "medium"
    assert osv_severity({}) == "medium"
    assert cvss3_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") == 9.8
    assert cvss3_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N") == 6.1
    assert cvss3_base_score("CVSS:2.0/AV:N") is None
