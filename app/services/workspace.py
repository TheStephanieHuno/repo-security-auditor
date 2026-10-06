"""Isolated, size-limited repository workspaces (SRS NFR-01, NFR-04).

Each scan gets a fresh temporary directory that is removed on every exit
path. Clones are shallow, single-branch, non-interactive, and check out
symlinks as plain files so repository content cannot point scanners at host
paths.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.scanners.base import (
    CheckError,
    resolve_executable,
    run_process,
    safe_diagnostic,
    scanner_environment,
)

MAX_REPOSITORY_BYTES = int(os.getenv("MAX_REPOSITORY_BYTES", str(100 * 1024 * 1024)))
CLONE_TIMEOUT_SECONDS = float(os.getenv("CLONE_TIMEOUT_SECONDS", "120"))

GITHUB_URL = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<name>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$"
)
_BRANCH = re.compile(r"^(?!-)(?!.*\.\.)(?!.*//)[A-Za-z0-9._/-]{1,255}(?<![./])$")


class WorkspaceError(CheckError):
    pass


def validate_branch(branch: str) -> str:
    if not _BRANCH.fullmatch(branch):
        raise ValueError("branch name contains unsupported characters")
    return branch


def _remove_readonly(function, path, _exception) -> None:  # noqa: ANN001 - shutil callback
    os.chmod(path, stat.S_IWRITE)
    function(path)


def directory_size(root: Path, limit: int) -> int:
    total = 0
    for directory, subdirectories, files in os.walk(root, followlinks=False):
        if ".git" in subdirectories and Path(directory) == root:
            subdirectories.remove(".git")
        for name in files:
            try:
                total += os.lstat(os.path.join(directory, name)).st_size
            except OSError:
                continue
            if total > limit:
                return total
    return total


@asynccontextmanager
async def repository_workspace(
    github_url: str, branch: str, *, commit_sha: str | None = None
) -> AsyncIterator[Path]:
    if not GITHUB_URL.fullmatch(github_url):
        raise WorkspaceError("only public https://github.com repositories can be scanned")
    validate_branch(branch)
    git = resolve_executable("git", "GIT_PATH")
    root = Path(tempfile.mkdtemp(prefix="rsa-scan-")).resolve()
    target = root / "repo"
    environment = scanner_environment(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_LFS_SKIP_SMUDGE": "1",
        }
    )
    try:
        result = await run_process(
            [
                git,
                "-c", "core.symlinks=false",
                "-c", "protocol.allow=never",
                "-c", "protocol.https.allow=always",
                "-c", "core.hooksPath=" + os.devnull,
                "clone",
                "--depth", "1",
                "--single-branch",
                "--no-tags",
                "--branch", branch,
                "--",
                github_url,
                str(target),
            ],
            cwd=root,
            timeout_seconds=CLONE_TIMEOUT_SECONDS,
            environment=environment,
        )
        if result.exit_code != 0:
            raise WorkspaceError(f"repository clone failed: {safe_diagnostic(result.stderr)}")
        if commit_sha:
            checkout = await run_process(
                [git, "-c", "core.symlinks=false", "fetch", "--depth", "1", "origin", commit_sha],
                cwd=target,
                timeout_seconds=CLONE_TIMEOUT_SECONDS,
                environment=environment,
            )
            if checkout.exit_code == 0:
                checkout = await run_process(
                    [git, "-c", "core.symlinks=false", "checkout", "--detach", commit_sha],
                    cwd=target,
                    timeout_seconds=CLONE_TIMEOUT_SECONDS,
                    environment=environment,
                )
            if checkout.exit_code != 0:
                raise WorkspaceError("requested commit could not be checked out")
        if directory_size(target, MAX_REPOSITORY_BYTES) > MAX_REPOSITORY_BYTES:
            raise WorkspaceError(
                f"repository exceeds the {MAX_REPOSITORY_BYTES // (1024 * 1024)} MB size limit"
            )
        yield target
    finally:
        shutil.rmtree(root, onexc=_remove_readonly)
