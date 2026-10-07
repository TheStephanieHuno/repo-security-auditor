"""Scanner engine tests: RSA-53 (base class), RSA-54/56 (wrappers), RSA-58 (OSV),
RSA-59 (config checks), RSA-60 (normalizer)."""

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import ClassVar

import httpx
import pytest

from app.db.models import Confidence, FindingCategory, ScannerName, Severity
from app.db.normalization import redact_sensitive_text
from app.scanners import default_checks
from app.scanners.base import CheckError, CheckStatus, SecurityCheck, run_checks, scanner_environment
from app.scanners.config_checks import ConfigCheck, scan_configuration
from app.scanners.gitleaks import GitleaksCheck
from app.scanners.normalizer import (
    Dependency,
    cvss3_base_score,
    normalize_gitleaks,
    normalize_osv,
    normalize_semgrep,
    relative_repository_path,
)
from app.scanners.osv import OsvCheck, parse_package_json, parse_requirements
from app.scanners.semgrep import SemgrepCheck

FIXTURES = Path(__file__).parent / "fixtures"
OUTPUTS = FIXTURES / "scanner_outputs"

# ------------------------------------------------------------ RSA-53 base


class _Check(SecurityCheck):
    timeout_seconds: ClassVar[float] = 0.2

    def __init__(self, name: ScannerName, behaviour: str) -> None:
        self.behaviour = behaviour
        self.__class__ = type(f"Check{name.value}", (_Check,), {"name": name})

    async def scan(self, workspace: Path):
        if self.behaviour == "crash":
            raise RuntimeError("password=hunter2 leaked in exception text")
        if self.behaviour == "error":
            raise CheckError("scanner exited with code 2: bad config")
        if self.behaviour == "hang":
            await asyncio.sleep(5)
        return []


@pytest.mark.asyncio
async def test_failures_are_isolated_per_check(tmp_path: Path) -> None:
    results = await run_checks(
        [
            _Check(ScannerName.GITLEAKS, "ok"),
            _Check(ScannerName.SEMGREP, "crash"),
            _Check(ScannerName.OSV, "error"),
            _Check(ScannerName.CONFIG, "hang"),
        ],
        tmp_path,
    )
    by_name = {result.scanner: result for result in results}
    assert by_name[ScannerName.GITLEAKS].status == CheckStatus.COMPLETED
    assert by_name[ScannerName.SEMGREP].status == CheckStatus.FAILED
    assert "hunter2" not in by_name[ScannerName.SEMGREP].error_summary
    assert by_name[ScannerName.OSV].error_summary == "scanner exited with code 2: bad config"
    assert by_name[ScannerName.CONFIG].status == CheckStatus.TIMEOUT


@pytest.mark.asyncio
async def test_run_checks_rejects_bad_input(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        await run_checks([], tmp_path / "missing")
    with pytest.raises(ValueError):
        await run_checks([_Check(ScannerName.OSV, "ok"), _Check(ScannerName.OSV, "ok")], tmp_path)


def test_registry_and_scanner_environment(monkeypatch) -> None:
    assert {check.name for check in default_checks()} == {
        ScannerName.GITLEAKS, ScannerName.SEMGREP, ScannerName.OSV, ScannerName.CONFIG,
    }
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@db/app")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    environment = scanner_environment()
    assert "DATABASE_URL" not in environment and "ANTHROPIC_API_KEY" not in environment


@pytest.mark.asyncio
async def test_missing_executable_fails_cleanly(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITLEAKS_PATH", str(tmp_path / "no-such-binary"))
    result = await GitleaksCheck().run(tmp_path)
    assert result.status == CheckStatus.FAILED
    assert "GITLEAKS_PATH" in result.error_summary


def test_wrapper_commands_are_hardened(tmp_path: Path) -> None:
    gitleaks = GitleaksCheck().command("gitleaks", tmp_path / "r.json")
    assert gitleaks[:3] == ["gitleaks", "dir", "."]
    assert "--redact" in gitleaks
    assert "--ignore-gitleaks-allow" in gitleaks
    assert gitleaks[gitleaks.index("--gitleaks-ignore-path") + 1] == str(tmp_path)
    semgrep = SemgrepCheck().command("semgrep")
    for flag in ("--metrics=off", "--disable-nosem", "--no-git-ignore", "--x-ignore-semgrepignore-files", "--json"):
        assert flag in semgrep
    assert all("registry" not in part and part != "auto" for part in semgrep)


# --------------------------------------------------------- RSA-60 normalizer


def test_relative_paths_cannot_escape_workspace(tmp_path: Path) -> None:
    assert relative_repository_path("src\\app.py", tmp_path) == "src/app.py"
    assert relative_repository_path(str(tmp_path / "src" / "a.py"), tmp_path) == "src/a.py"
    for bad in ("../etc/passwd", str(tmp_path.parent / "other.py"), "/etc/passwd"):
        with pytest.raises(ValueError):
            relative_repository_path(bad, tmp_path)


def test_gitleaks_normalization_masks_secrets() -> None:
    entry = {
        "RuleID": "rsa-github-token",
        "Description": "GitHub token",
        "File": "config.py",
        "StartLine": 3,
        "EndLine": 3,
        "Match": "GITHUB_TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz0123456789'",
        "Secret": "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        "Tags": ["github", "severity:critical"],
    }
    [finding] = normalize_gitleaks([entry], Path("."))
    blob = json.dumps(finding.__dict__, default=str)
    assert "abcdefghijklmnop" not in blob
    assert finding.evidence[0].matched_value_redacted == "ghp_********"
    assert (finding.severity, finding.category) == (Severity.CRITICAL, FindingCategory.SECRET)
    # The title must survive persistence-time redaction unchanged (regression: "secret: X" was masked).
    assert redact_sensitive_text(finding.title) == finding.title == "Hardcoded secret detected (GitHub token)"
    untagged = normalize_gitleaks([{**entry, "Tags": []}], Path("."))[0]
    assert untagged.severity == Severity.HIGH
    with pytest.raises(ValueError):
        normalize_gitleaks([{**entry, "RuleID": ""}], Path("."))
    with pytest.raises(ValueError):
        normalize_gitleaks({"not": "a list"}, Path("."))


def test_semgrep_normalization_rule_ids_and_snippets(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("x = 1\neval(user_input)\n")
    report = {
        "results": [
            {
                "check_id": "c.Users.me.rules.rsa-python-eval-exec",
                "path": "app.py",
                "start": {"line": 2},
                "end": {"line": 2},
                "extra": {
                    "message": "eval of input",
                    "severity": "ERROR",
                    "lines": "requires login",
                    "metadata": {"title": "Eval", "confidence": "MEDIUM", "cwe": ["CWE-95"]},
                },
            }
        ]
    }
    [finding] = normalize_semgrep(report, tmp_path)
    assert finding.rule_id == "rsa-python-eval-exec"
    assert finding.severity == Severity.HIGH
    assert finding.confidence == Confidence.MEDIUM
    assert finding.evidence[0].code_snippet == "eval(user_input)"
    assert "CWE-95" in finding.description
    with pytest.raises(ValueError):
        normalize_semgrep({"errors": []}, tmp_path)


def test_cvss_base_scores_match_reference_values() -> None:
    assert cvss3_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") == 9.8
    assert cvss3_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N") == 6.1
    assert cvss3_base_score("CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N") == 5.5
    assert cvss3_base_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N") == 0.0
    assert cvss3_base_score("CVSS:2.0/AV:N") is None


def test_osv_normalization_deduplicates_aliases_and_recommends_fix() -> None:
    dependency = Dependency("PyPI", "django", "3.2.0", "requirements.txt", line=1)
    ghsa = {
        "id": "GHSA-xxxx-yyyy-zzzz",
        "aliases": ["CVE-2021-1234", "PYSEC-2021-1"],
        "summary": "SQL injection",
        "database_specific": {"severity": "MODERATE"},
        "affected": [{"package": {"name": "django"}, "ranges": [{"events": [{"introduced": "0"}, {"fixed": "3.2.5"}]}]}],
    }
    pysec = {"id": "PYSEC-2021-1", "aliases": ["CVE-2021-1234"], "summary": "dup"}
    cvss_only = {
        "id": "PYSEC-2022-9",
        "summary": "Remote code execution",
        "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}],
    }
    findings = normalize_osv([(dependency, pysec), (dependency, ghsa), (dependency, cvss_only)])
    assert [f.rule_id for f in findings] == ["GHSA-xxxx-yyyy-zzzz", "PYSEC-2022-9"]
    assert findings[0].severity == Severity.MEDIUM
    assert findings[0].recommendation == "Upgrade django to 3.2.5 or later."
    assert "CVE-2021-1234" in findings[0].description
    assert findings[1].severity == Severity.CRITICAL

    loose = Dependency("npm", "lodash", "4.17.15", "package.json", exact=False)
    [ranged] = normalize_osv([(loose, ghsa)])
    assert ranged.confidence == Confidence.MEDIUM


# ------------------------------------------------------------ RSA-58 OSV


def test_manifest_parsing() -> None:
    requirements = parse_requirements(
        "Django==3.2.0  # pinned\nrequests[socks]==2.19.0\nflask>=2.0\n-r other.txt\n"
        "git+https://x/y.git\nnumpy==1.26.0; python_version > '3.8'\n",
        "requirements.txt",
    )
    assert [(d.name, d.version, d.line) for d in requirements] == [
        ("django", "3.2.0", 1), ("requests", "2.19.0", 2), ("numpy", "1.26.0", 6)
    ]
    package = parse_package_json(
        json.dumps({"dependencies": {"lodash": "4.17.15", "express": "^4.17.1", "x": "latest",
                                     "y": "git+https://a/b"}, "devDependencies": {"jest": "~29.0.0"}}, indent=2),
        "package.json",
    )
    assert [(d.name, d.version, d.exact) for d in package] == [
        ("lodash", "4.17.15", True), ("express", "4.17.1", False), ("jest", "29.0.0", False)
    ]
    assert parse_package_json("{not json", "package.json") == []


def _osv_transport(calls: list):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/v1/querybatch":
            queries = json.loads(request.content)["queries"]
            return httpx.Response(200, json={"results": [
                {"vulns": [{"id": "GHSA-aaaa-bbbb-cccc"}, {"id": "../../evil"}]}
                if q["package"]["name"] == "lodash" else {}
                for q in queries
            ]})
        if request.url.path == "/v1/vulns/GHSA-aaaa-bbbb-cccc":
            return httpx.Response(200, json={
                "id": "GHSA-aaaa-bbbb-cccc", "summary": "Prototype pollution",
                "database_specific": {"severity": "HIGH"},
                "affected": [{"package": {"name": "lodash"}, "ranges": [{"events": [{"fixed": "4.17.21"}]}]}],
            })
        return httpx.Response(404)
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_osv_check_queries_api_and_ignores_unsafe_ids(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"lodash": "4.17.15", "react": "18.2.0"}}))
    calls: list = []
    result = await OsvCheck(transport=_osv_transport(calls)).run(tmp_path)
    assert result.status == CheckStatus.COMPLETED
    [finding] = result.findings
    assert finding.severity == Severity.HIGH
    assert finding.recommendation == "Upgrade lodash to 4.17.21 or later."
    assert all("evil" not in path for _, path in calls)


@pytest.mark.asyncio
async def test_osv_outage_fails_the_check(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("django==3.2.0\n")
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    result = await OsvCheck(transport=transport).run(tmp_path)
    assert result.status == CheckStatus.FAILED
    assert "OSV API unavailable" in result.error_summary


@pytest.mark.asyncio
async def test_osv_without_manifests_makes_no_requests(tmp_path: Path) -> None:
    def fail(request):  # pragma: no cover - must not be called
        raise AssertionError("no request expected")
    result = await OsvCheck(transport=httpx.MockTransport(fail)).run(tmp_path)
    assert (result.status, result.findings) == (CheckStatus.COMPLETED, ())


# ---------------------------------------------------- RSA-59 config checks


def test_config_checks_detect_env_debug_and_cors(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATABASE_PASSWORD=s3cr3t-value\nDEBUG=true\n")
    (tmp_path / ".env.example").write_text("DATABASE_PASSWORD=\n")
    (tmp_path / "app.py").write_text(
        "from fastapi.middleware.cors import CORSMiddleware\n"
        "app.add_middleware(\n    CORSMiddleware,\n    allow_origins=['*'],\n    allow_credentials=True,\n)\n"
        "app.run(debug=True)\n"
    )
    (tmp_path / "settings.py").write_text("DEBUG = True\nCORS_ALLOW_ALL_ORIGINS = True\n")
    (tmp_path / "server.js").write_text("app.use(cors());\napp.use(cors({ origin: '*' }));\n")
    (tmp_path / "config.yaml").write_text("debug: true\n")
    (tmp_path / "safe.py").write_text("app.add_middleware(CORSMiddleware, allow_origins=['https://app.example.com'])\n")

    issues = scan_configuration(tmp_path)
    by_rule: dict[str, list] = {}
    for issue in issues:
        by_rule.setdefault(issue.rule_id, []).append(issue)

    [env_issue] = by_rule["rsa-config-committed-env-file"]
    assert env_issue.severity == Severity.HIGH
    assert "DATABASE_PASSWORD" in env_issue.snippet and "s3cr3t-value" not in env_issue.snippet
    assert by_rule["rsa-config-flask-debug"][0].line == 7
    assert by_rule["rsa-config-django-debug"][0].file_path == "settings.py"
    assert by_rule["rsa-config-debug-flag"][0].file_path == "config.yaml"
    wildcard = {(i.file_path, i.severity) for i in by_rule["rsa-config-cors-wildcard"]}
    assert ("app.py", Severity.HIGH) in wildcard  # escalated: credentials allowed
    assert ("server.js", Severity.MEDIUM) in wildcard
    assert by_rule["rsa-config-cors-allow-all"][0].file_path == "settings.py"
    assert by_rule["rsa-config-cors-default"][0].file_path == "server.js"
    assert all(issue.file_path != "safe.py" for issue in issues)
    assert all(issue.file_path != ".env.example" for issue in issues)


def test_config_checks_skip_vendor_dirs_and_symlinks(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.py").write_text("DEBUG = True\n")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("DEBUG = True\n")
    try:
        os.symlink(outside, tmp_path / "linked.py")
    except (OSError, NotImplementedError):
        pass  # symlinks need privileges on Windows; the vendor-dir check still runs
    assert scan_configuration(tmp_path) == []
    outside.unlink()


@pytest.mark.asyncio
async def test_config_check_returns_normalized_findings(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("app.run(host='0.0.0.0', debug=True)\n")
    result = await ConfigCheck().run(tmp_path)
    [finding] = result.findings
    assert (finding.category, finding.severity, finding.file_path) == (
        FindingCategory.CONFIGURATION, Severity.HIGH, "main.py"
    )
    assert len(finding.fingerprint) == 64


# ------------------------------------- real binaries (opt-in: *_PATH env)


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GITLEAKS_PATH"), reason="set GITLEAKS_PATH to run against real gitleaks")
async def test_real_gitleaks_scan(tmp_path: Path) -> None:
    token = "ghp_" + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7bC0eF3hJ6"
    (tmp_path / "config.py").write_text(f'GITHUB_TOKEN = "{token}"\n')
    result = await GitleaksCheck().run(tmp_path)
    assert result.status == CheckStatus.COMPLETED, result.error_summary
    [finding] = result.findings
    assert finding.rule_id == "rsa-github-token" and finding.file_path == "config.py"
    assert token not in json.dumps([e.__dict__ for e in finding.evidence], default=str)


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("GITLEAKS_PATH"), reason="set GITLEAKS_PATH to run against real gitleaks")
async def test_real_gitleaks_ignores_repository_suppressions(tmp_path: Path) -> None:
    """A scanned repository must not be able to hide its own secrets."""
    inline = "ghp_" + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7bC0eF3hJ6"
    listed = "ghp_" + "Zy9xW8vU7tS6rQ5pO4nM3lK2jI1hG0fE9dC8"
    (tmp_path / "inline.py").write_text(f'A = "{inline}"  # gitleaks:allow\n')
    (tmp_path / "listed.py").write_text(f'B = "{listed}"\n')
    (tmp_path / ".gitleaksignore").write_text("listed.py:rsa-github-token:1\n")
    result = await GitleaksCheck().run(tmp_path)
    assert result.status == CheckStatus.COMPLETED, result.error_summary
    assert sorted(f.file_path for f in result.findings) == ["inline.py", "listed.py"]


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("SEMGREP_PATH"), reason="set SEMGREP_PATH to run against real semgrep")
async def test_real_semgrep_scan(tmp_path: Path) -> None:
    shutil.copy(FIXTURES / "semgrep" / "python.py", tmp_path / "app.py")
    result = await SemgrepCheck().run(tmp_path)
    assert result.status == CheckStatus.COMPLETED, result.error_summary
    assert {f.rule_id for f in result.findings} >= {"rsa-python-eval-exec", "rsa-python-sql-string-building"}
    assert all(f.evidence[0].code_snippet for f in result.findings)


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("SEMGREP_PATH"), reason="set SEMGREP_PATH to run against real semgrep")
async def test_real_semgrep_ignores_repository_suppressions(tmp_path: Path) -> None:
    """.semgrepignore and nosemgrep comments in the scanned repository are not honoured."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("eval(user_input)\neval(other)  # nosemgrep\n")
    (tmp_path / ".semgrepignore").write_text("src/\n")
    result = await SemgrepCheck().run(tmp_path)
    assert result.status == CheckStatus.COMPLETED, result.error_summary
    assert [f.line_start for f in result.findings] == [1, 2]
