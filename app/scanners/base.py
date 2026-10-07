"""Pluggable security-check interface (SRS NFR-03, NFR-05).

Every scanner implements ``SecurityCheck.scan``. ``SecurityCheck.run`` wraps it
so that a crash, timeout, or missing executable becomes a FAILED/TIMEOUT
``CheckResult`` for that scanner only; ``run_checks`` runs checks concurrently
and never lets one failure discard another check's results.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from app.db.models import ScannerName
from app.db.normalization import NormalizedFinding, redact_sensitive_text

logger = logging.getLogger(__name__)

MAX_PROCESS_OUTPUT_BYTES = 50 * 1024 * 1024
MAX_ERROR_SUMMARY_LENGTH = 500

# Directories never worth scanning and often huge.
SKIPPED_DIRECTORIES = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox"}
)

# Only these variables reach scanner processes, so application secrets
# (DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY, ...) are never exposed to them.
_INHERITED_ENVIRONMENT = (
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "TMPDIR",
    "HOME",
    "USERPROFILE",
    "LANG",
    "LC_ALL",
)


class CheckStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class CheckResult:
    scanner: ScannerName
    status: CheckStatus
    findings: tuple[NormalizedFinding, ...] = field(default_factory=tuple)
    error_summary: str | None = None


class CheckError(Exception):
    """A scanner failure whose message is safe to persist and show to users."""


class CheckTimeout(CheckError):
    pass


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int
    stdout: bytes
    stderr: bytes


def scanner_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = {
        name: os.environ[name] for name in _INHERITED_ENVIRONMENT if name in os.environ
    }
    environment.update(extra or {})
    return environment


def resolve_executable(name: str, override_variable: str) -> str:
    """Find a scanner binary from an explicit override or PATH."""
    configured = os.getenv(override_variable)
    if configured:
        if Path(configured).is_file():
            return configured
        raise CheckError(f"{name} executable configured in {override_variable} was not found")
    found = shutil.which(name)
    if found is None:
        raise CheckError(f"{name} executable not found on PATH")
    return found


async def run_process(
    arguments: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    environment: dict[str, str] | None = None,
) -> ProcessResult:
    """Run a fixed argument list (never a shell string) with a hard timeout."""
    process = await asyncio.create_subprocess_exec(
        *arguments,
        cwd=str(cwd),
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=environment if environment is not None else scanner_environment(),
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise CheckTimeout(f"scanner exceeded the {timeout_seconds:.0f}s time limit") from None
    if len(stdout) > MAX_PROCESS_OUTPUT_BYTES:
        raise CheckError("scanner output exceeded the size limit")
    return ProcessResult(exit_code=process.returncode or 0, stdout=stdout, stderr=stderr)


def safe_diagnostic(message: str | bytes) -> str:
    """Reduce scanner stderr to a short, redacted, single-paragraph summary."""
    if isinstance(message, bytes):
        message = message.decode("utf-8", errors="replace")
    collapsed = " ".join(message.split())
    return redact_sensitive_text(collapsed, max_length=MAX_ERROR_SUMMARY_LENGTH) or ""


def iter_workspace_files(
    workspace: Path, *, max_file_bytes: int, max_files: int = 20_000
) -> Iterator[Path]:
    """Yield regular files inside the workspace without following symlinks.

    Repository content is untrusted: a symlink could point at host files such as
    ``/etc/passwd``, so links are skipped entirely.
    """
    root = workspace.resolve()
    seen = 0
    for directory, subdirectories, files in os.walk(root, followlinks=False):
        subdirectories[:] = [
            name
            for name in subdirectories
            if name not in SKIPPED_DIRECTORIES and not (Path(directory) / name).is_symlink()
        ]
        for name in files:
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                continue
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            seen += 1
            if seen > max_files:
                return
            yield path


class SecurityCheck(ABC):
    """Base class for one independent scanner."""

    name: ClassVar[ScannerName]
    timeout_seconds: ClassVar[float] = 180.0

    @abstractmethod
    async def scan(self, workspace: Path) -> list[NormalizedFinding]:
        """Scan the workspace and return normalized findings.

        Raise ``CheckError`` with a user-safe message for expected failures.
        """

    async def run(self, workspace: Path) -> CheckResult:
        try:
            findings = await asyncio.wait_for(self.scan(workspace), timeout=self.timeout_seconds)
        except (asyncio.TimeoutError, CheckTimeout):
            return CheckResult(
                scanner=self.name,
                status=CheckStatus.TIMEOUT,
                error_summary=f"{self.name.value.lower()} exceeded the time limit",
            )
        except CheckError as error:
            return CheckResult(
                scanner=self.name,
                status=CheckStatus.FAILED,
                error_summary=safe_diagnostic(str(error)) or "scanner failed",
            )
        except Exception:
            # Unexpected errors can carry repository content in their message,
            # so only the type is persisted; details go to the server log.
            logger.exception("security check %s crashed", self.name.value)
            return CheckResult(
                scanner=self.name,
                status=CheckStatus.FAILED,
                error_summary=f"{self.name.value.lower()} failed with an internal error",
            )
        return CheckResult(
            scanner=self.name, status=CheckStatus.COMPLETED, findings=tuple(findings)
        )


async def run_checks(checks: Sequence[SecurityCheck], workspace: Path) -> list[CheckResult]:
    """Run checks concurrently; each result is independent of the others."""
    if not workspace.is_dir():
        raise ValueError("workspace must be an existing directory")
    names = [check.name for check in checks]
    if len(set(names)) != len(names):
        raise ValueError("each scanner may only be registered once")
    return list(await asyncio.gather(*(check.run(workspace) for check in checks)))
