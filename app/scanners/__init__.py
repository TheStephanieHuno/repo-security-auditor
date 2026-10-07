"""Pluggable security scanners and their registry."""

from app.scanners.base import CheckResult, CheckStatus, SecurityCheck, run_checks
from app.scanners.config_checks import ConfigCheck
from app.scanners.gitleaks import GitleaksCheck
from app.scanners.osv import OsvCheck
from app.scanners.semgrep import SemgrepCheck


def default_checks() -> list[SecurityCheck]:
    """The MVP scanner set. Add a new scanner by appending its SecurityCheck here."""
    return [GitleaksCheck(), SemgrepCheck(), OsvCheck(), ConfigCheck()]


__all__ = [
    "CheckResult",
    "CheckStatus",
    "ConfigCheck",
    "GitleaksCheck",
    "OsvCheck",
    "SecurityCheck",
    "SemgrepCheck",
    "default_checks",
    "run_checks",
]
