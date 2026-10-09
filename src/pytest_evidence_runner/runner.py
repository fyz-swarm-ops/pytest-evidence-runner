from __future__ import annotations

import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .hashing import hash_files
from .models import RunMetadata, VerificationReport


def run_verification(
    command: list[str],
    workdir: Path,
    hash_patterns: list[str] | None = None,
    timeout_seconds: int | None = None,
) -> VerificationReport:
    if not command:
        raise ValueError("command must not be empty")
    workdir = workdir.resolve()
    if not workdir.exists():
        raise FileNotFoundError(f"workdir does not exist: {workdir}")
    if not workdir.is_dir():
        raise NotADirectoryError(f"workdir is not a directory: {workdir}")

    started = datetime.now(timezone.utc)
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    hashes = hash_files(workdir, hash_patterns or [])
    try:
        completed = subprocess.run(
            command,
            cwd=workdir,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = _timeout_output(exc.stdout)
        stderr = _timeout_output(exc.stderr)
        stderr = (stderr + "\n" if stderr else "") + f"Command timed out after {timeout_seconds} seconds."

    finished = datetime.now(timezone.utc)
    duration = round((finished - started).total_seconds(), 3)
    verdict = "passed" if exit_code == 0 else "failed"
    failure_kind = None if exit_code == 0 else ("timeout" if exit_code == 124 else "runner_error")
    summary = "Command completed successfully." if exit_code == 0 else f"Command failed with exit code {exit_code}."

    return VerificationReport(
        schema_version="1.0",
        run_id=run_id,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_seconds=duration,
        workdir=str(workdir),
        command=command,
        exit_code=exit_code,
        verdict=verdict,
        failure_kind=failure_kind,
        summary=summary,
        stdout=stdout,
        stderr=stderr,
        execution_mode="local",
        file_hashes=hashes,
        metadata=RunMetadata(
            python=sys.version.split()[0],
            platform=platform.platform(),
            executable=sys.executable,
        ),
    )


def _timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
