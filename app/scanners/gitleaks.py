"""Gitleaks secret scanner wrapper (SRS FR-04, ticket T-17).

Requires gitleaks >= 8.19 (``gitleaks dir``). Set ``GITLEAKS_PATH`` to use a
binary that is not on PATH.
"""

from __future__ import annotations

import json
import tempfile
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
)
from app.scanners.normalizer import normalize_gitleaks

RULES_PATH = Path(__file__).parent / "rules" / "gitleaks.toml"
IGNORE_FILE_NAME = ".gitleaksignore"


class GitleaksCheck(SecurityCheck):
    name: ClassVar[ScannerName] = ScannerName.GITLEAKS
    timeout_seconds: ClassVar[float] = 180.0

    def __init__(self, *, rules_path: Path = RULES_PATH, max_file_megabytes: int = 5) -> None:
        self.rules_path = rules_path
        self.max_file_megabytes = max_file_megabytes

    def command(self, executable: str, report_path: Path) -> list[str]:
        return [
            executable,
            "dir",
            ".",
            "--config",
            str(self.rules_path.resolve()),
            "--report-format",
            "json",
            "--report-path",
            str(report_path),
            # Gitleaks replaces secret values before they leave the process.
            "--redact",
            # Repository content must not be able to hide its own secrets:
            # ignore inline "gitleaks:allow" comments, and read .gitleaksignore
            # from our empty report directory instead of the scanned repository.
            "--ignore-gitleaks-allow",
            "--gitleaks-ignore-path",
            str(report_path.parent),
            "--exit-code",
            "0",
            "--no-banner",
            "--log-level",
            "error",
            "--max-target-megabytes",
            str(self.max_file_megabytes),
        ]

    async def scan(self, workspace: Path) -> list[NormalizedFinding]:
        executable = resolve_executable("gitleaks", "GITLEAKS_PATH")
        # Gitleaks always honours a .gitleaksignore at the scan root, whatever
        # --gitleaks-ignore-path says. The workspace is a disposable clone, so
        # drop the repository's file rather than let it suppress findings.
        (workspace / IGNORE_FILE_NAME).unlink(missing_ok=True)
        # The report lives outside the workspace so repository content cannot
        # pre-create or symlink the report path.
        with tempfile.TemporaryDirectory(prefix="rsa-gitleaks-") as report_directory:
            report_path = Path(report_directory) / "report.json"
            result = await run_process(
                self.command(executable, report_path),
                cwd=workspace,
                timeout_seconds=self.timeout_seconds,
            )
            if result.exit_code != 0:
                raise CheckError(
                    f"gitleaks exited with code {result.exit_code}: "
                    f"{safe_diagnostic(result.stderr) or 'no diagnostic output'}"
                )
            try:
                report = json.loads(report_path.read_text(encoding="utf-8") or "[]")
            except FileNotFoundError:
                raise CheckError("gitleaks did not produce a report") from None
            except json.JSONDecodeError:
                raise CheckError("gitleaks produced a malformed report") from None
        try:
            return normalize_gitleaks(report, workspace)
        except ValueError as error:
            raise CheckError(f"gitleaks report rejected: {error}") from None
