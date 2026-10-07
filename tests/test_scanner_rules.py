"""RSA-55 (O-07) Gitleaks rules, RSA-57 (O-08) Semgrep rules, and RSA-70 (O-14)
severity validation of recorded real scanner output."""

import json
import os
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

import pytest
import yaml

from app.db.models import Severity
from app.scanners.gitleaks import RULES_PATH as GITLEAKS_RULES
from app.scanners.normalizer import normalize_gitleaks, normalize_semgrep
from app.scanners.semgrep import RULES_DIRECTORY as SEMGREP_RULES

FIXTURES = Path(__file__).parent / "fixtures"

# Built at runtime so this file does not itself contain scannable secrets.
GITHUB_TOKEN = "ghp_" + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7bC0eF3hJ6"
AWS_KEY_ID = "AKIA" + "IOSFODNN7EXAMPLQ"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/" + "bPxRfiCYzEXAMPLEKQ"
PRIVATE_KEY = (
    "-----BEGIN RSA PRIVATE KEY-----\n" + "MIIEowIBAAKCAQEAu1SU1LfVLPHCozMxH2Mo4lgOEePzNm0tRgeLezV6ffAt\n" * 2
    + "-----END RSA PRIVATE KEY-----"
)

GITLEAKS_CASES = {
    "rsa-aws-access-key-id": ([f'key = "{AWS_KEY_ID}"'], ["AKIA_NOT_A_KEY", "AKIA1234"]),
    "rsa-aws-secret-access-key": (
        [f'aws_secret_access_key = "{AWS_SECRET}"', f"AWS_SECRET_ACCESS_KEY={AWS_SECRET}"],
        ["aws_secret_access_key = ${AWS_SECRET}"],
    ),
    "rsa-github-token": ([f"token: {GITHUB_TOKEN}"], ["ghp_short", "github_token = ''"]),
    "rsa-github-fine-grained-token": (["github_pat_" + "A1b2C3d4E5" * 8 + "Xy"], ["github_pat_abc"]),
    "rsa-database-url-password": (
        ["postgresql://app:Hunter2Secret@db.internal:5432/app", "mongodb+srv://u:Pw9xYz@cluster0/db"],
        ["postgresql://app:${DB_PASS}@db/app", "postgres://user:password@localhost/db",
         "postgres://localhost/db", "mysql://app:<password>@db/app"],
    ),
    "rsa-database-password-assignment": (
        ['DB_PASSWORD = "S3cure!Pass9"', "postgres_password: 'Xk29-qq81'"],
        ['DB_PASSWORD = "changeme"', 'DB_PASSWORD = "${SECRET}"', 'user_password = "S3cure!Pass9"'],
    ),
    "rsa-private-key": ([PRIVATE_KEY], ["-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----"]),
}


def _gitleaks_rules() -> dict[str, dict]:
    return {rule["id"]: rule for rule in tomllib.loads(GITLEAKS_RULES.read_text())["rules"]}


def _matches(rule: dict, text: str) -> bool:
    match = re.search(rule["regex"], text)
    if not match:
        return False
    secret = match.group(rule.get("secretGroup", 0))
    allowlist = rule.get("allowlist", {})
    return not any(re.search(pattern, secret) for pattern in allowlist.get("regexes", []))


def test_gitleaks_config_extends_defaults_without_duplicates() -> None:
    config = tomllib.loads(GITLEAKS_RULES.read_text())
    assert config["extend"]["useDefault"] is True
    assert {"aws-access-token", "github-pat", "private-key"} <= set(config["extend"]["disabledRules"])
    assert set(_gitleaks_rules()) == set(GITLEAKS_CASES)


@pytest.mark.parametrize("rule_id", sorted(GITLEAKS_CASES))
def test_gitleaks_rule_matches_positives_and_rejects_negatives(rule_id: str) -> None:
    rule = _gitleaks_rules()[rule_id]
    assert re.search(r"^severity:(low|medium|high|critical)$", " ".join(rule["tags"]).split()[-1])
    assert rule["keywords"], "keywords keep gitleaks fast"
    positives, negatives = GITLEAKS_CASES[rule_id]
    for sample in positives:
        assert _matches(rule, sample), f"{rule_id} missed: {sample[:40]}"
    for sample in negatives:
        assert not _matches(rule, sample), f"{rule_id} false positive: {sample[:40]}"


ALLOWED_SEMGREP_SEVERITIES = {"INFO", "WARNING", "ERROR"}


def _semgrep_rules() -> list[dict]:
    return [rule for path in sorted(SEMGREP_RULES.glob("*.yml")) for rule in yaml.safe_load(path.read_text())["rules"]]


def test_semgrep_rules_are_well_formed() -> None:
    rules = _semgrep_rules()
    ids = [rule["id"] for rule in rules]
    assert len(ids) == len(set(ids))
    languages = {language for rule in rules for language in rule["languages"]}
    assert {"python", "javascript", "typescript"} <= languages
    for rule in rules:
        assert rule["id"].startswith("rsa-")
        assert rule["severity"] in ALLOWED_SEMGREP_SEVERITIES
        assert rule["message"].strip()
        metadata = rule["metadata"]
        assert metadata["title"] and metadata["recommendation"]
        assert metadata["confidence"] in {"LOW", "MEDIUM", "HIGH"}
        assert any(cwe.startswith("CWE-") for cwe in metadata["cwe"])


def test_every_semgrep_rule_has_annotated_test_cases() -> None:
    annotations = "".join(path.read_text() for path in sorted((FIXTURES / "semgrep").glob("*.[pj][ys]")))
    for rule in _semgrep_rules():
        assert f"ruleid: {rule['id']}" in annotations, rule["id"]


@pytest.mark.skipif(not os.getenv("SEMGREP_PATH"), reason="set SEMGREP_PATH to run semgrep --test")
def test_semgrep_rule_unit_tests_pass() -> None:
    result = subprocess.run(
        [os.environ["SEMGREP_PATH"], "--test", "--metrics=off", "--config", str(SEMGREP_RULES),
         str(FIXTURES / "semgrep")],
        capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"}, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All tests passed" in result.stdout + result.stderr


# ------------------------- RSA-70: severity validation of recorded output
#
# tests/fixtures/scanner_outputs/*.json were produced by gitleaks 8.30.1 and
# semgrep 1.179.0 running these rules against a sample repository.

EXPECTED_SEMGREP_SEVERITY = {
    "rsa-python-eval-exec": Severity.HIGH,
    "rsa-python-subprocess-shell-true": Severity.HIGH,
    "rsa-python-sql-string-building": Severity.HIGH,
    "rsa-python-os-system": Severity.MEDIUM,
    "rsa-python-pickle-load": Severity.MEDIUM,
    "rsa-python-yaml-unsafe-load": Severity.MEDIUM,
    "rsa-python-tls-verification-disabled": Severity.MEDIUM,
    "rsa-js-eval": Severity.HIGH,
    "rsa-js-child-process-exec": Severity.HIGH,
    "rsa-js-sql-string-building": Severity.HIGH,
    "rsa-js-new-function": Severity.MEDIUM,
    "rsa-js-dom-xss-sink": Severity.MEDIUM,
    "rsa-js-tls-verification-disabled": Severity.MEDIUM,
}
EXPECTED_GITLEAKS_SEVERITY = {
    "rsa-aws-access-key-id": Severity.CRITICAL,
    "rsa-aws-secret-access-key": Severity.CRITICAL,
    "rsa-github-token": Severity.CRITICAL,
    "rsa-private-key": Severity.CRITICAL,
    "rsa-database-url-password": Severity.HIGH,
    "rsa-database-password-assignment": Severity.HIGH,
}


def test_recorded_semgrep_output_maps_to_expected_severities(tmp_path: Path) -> None:
    report = json.loads((FIXTURES / "scanner_outputs" / "semgrep.json").read_text())
    findings = normalize_semgrep(report, tmp_path)
    assert len(findings) == len(report["results"])
    assert {f.rule_id for f in findings} == set(EXPECTED_SEMGREP_SEVERITY)
    for finding in findings:
        assert finding.severity == EXPECTED_SEMGREP_SEVERITY[finding.rule_id], finding.rule_id
        assert not finding.file_path.startswith("/") and "\\" not in finding.file_path
    # Every ruleid annotation in the fixtures produced exactly one result.
    annotation = re.compile(r"^\s*(?:#|//)\s*ruleid:\s*(rsa-[\w-]+)\s*$")
    annotated = Counter(
        match.group(1)
        for path in sorted((FIXTURES / "semgrep").glob("*.[pj][ys]"))
        for line in path.read_text().splitlines()
        if (match := annotation.match(line))
    )
    assert Counter(f.rule_id for f in findings) == annotated


def test_recorded_gitleaks_output_maps_to_expected_severities(tmp_path: Path) -> None:
    entries = json.loads((FIXTURES / "scanner_outputs" / "gitleaks.json").read_text())
    findings = normalize_gitleaks(entries, tmp_path)
    assert {f.rule_id for f in findings} == set(EXPECTED_GITLEAKS_SEVERITY)
    for finding in findings:
        assert finding.severity == EXPECTED_GITLEAKS_SEVERITY[finding.rule_id]
        assert finding.evidence[0].matched_value_redacted == "REDACTED"
    serialized = json.dumps([f.evidence[0].code_snippet for f in findings])
    for secret in ("Hunter2Secret", "S3cure!Pass9", AWS_KEY_ID, GITHUB_TOKEN):
        assert secret not in serialized
