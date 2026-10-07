"""Semgrep code-pattern scanner wrapper (SRS FR-04, ticket T-18).

Runs the project's local rules only (no registry download, metrics off).
Set ``SEMGREP_PATH`` to use a binary that is not on PATH.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from app.db.models import ScannerName
from app.db.normalization import NormalizedFinding
from app.scanners.base import (
    CheckError,
    SecurityCheck,
    resolve_executable,
    run_process,
    safe_diagnostic,
    scanner_environment,
)
from app.scanners.normalizer import normalize_semgrep

RULES_DIRECTORY = Path(__file__).parent / "rules" / "semgrep"


class SemgrepCheck(SecurityCheck):
    name: ClassVar[ScannerName] = ScannerName.SEMGREP
    timeout_seconds: ClassVar[float] = 240.0

    def __init__(
        self,
        *,
        rules_directory: Path = RULES_DIRECTORY,
        per_file_timeout_seconds: int = 30,
        max_target_bytes: int = 1_000_000,
    ) -> None:
        self.rules_directory = rules_directory
        self.per_file_timeout_seconds = per_file_timeout_seconds
        self.max_target_bytes = max_target_bytes

    def command(self, executable: str) -> list[str]:
        return [
            executable,
            "scan",
            "--config",
            str(self.rules_directory.resolve()),
            "--json",
            "--quiet",
            "--metrics=off",
            "--disable-version-check",
            # Repository content must not be able to silence findings.
            "--disable-nosem",
            "--no-git-ignore",
            "--x-ignore-semgrepignore-files",
            "--timeout",
            str(self.per_file_timeout_seconds),
            "--max-target-bytes",
            str(self.max_target_bytes),
            ".",
        ]

    async def scan(self, workspace: Path) -> list[NormalizedFinding]:
        executable = resolve_executable("semgrep", "SEMGREP_PATH")
        result = await run_process(
            self.command(executable),
            cwd=workspace,
            timeout_seconds=self.timeout_seconds,
            environment=scanner_environment(
                {"PYTHONUTF8": "1", "SEMGREP_SEND_METRICS": "off", "SEMGREP_ENABLE_VERSION_CHECK": "0"}
            ),
        )
        try:
            report = json.loads(result.stdout.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise CheckError(
                f"semgrep produced malformed output (exit code {result.exit_code}): "
                f"{safe_diagnostic(result.stderr)}"
            ) from None

        if result.exit_code != 0:
            errors = report.get("errors") if isinstance(report, dict) else None
            first = errors[0] if isinstance(errors, list) and errors else {}
            message = first.get("message") if isinstance(first, dict) else None
            raise CheckError(
                f"semgrep exited with code {result.exit_code}: "
                f"{safe_diagnostic(message or result.stderr) or 'no diagnostic output'}"
            )
        try:
            return normalize_semgrep(report, workspace)
        except ValueError as error:
            raise CheckError(f"semgrep report rejected: {error}") from None
