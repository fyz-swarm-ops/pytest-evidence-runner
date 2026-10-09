from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from importlib.resources import as_file, files
from pathlib import Path

from .hashing import hash_files
from .models import (
    ContainerEnvironment,
    EvidenceLog,
    FailureRecord,
    FileHash,
    TestCaseRecord,
    TestSession,
    VerificationReport,
)
from .text import timeout_output

DEFAULT_IMAGE = "pytest-evidence-runner:local"
DEFAULT_PYTEST_COMMAND = ["python", "-m", "pytest", "-q"]
RESOURCE_LIMITS = {
    "cpus": "1",
    "memory": "512m",
    "pids_limit": "256",
    "tmpfs": "/tmp:rw,nosuid,nodev,size=128m",
}


def build_docker_command(image: str, project_path: Path, output_path: Path, command: list[str]) -> list[str]:
    if not command:
        command = DEFAULT_PYTEST_COMMAND
    junit_path = "/evidence/raw/pytest-junit.xml"
    pytest_command = _with_junitxml(command, junit_path)
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cpus",
        RESOURCE_LIMITS["cpus"],
        "--memory",
        RESOURCE_LIMITS["memory"],
        "--pids-limit",
        RESOURCE_LIMITS["pids_limit"],
        "--tmpfs",
        RESOURCE_LIMITS["tmpfs"],
        "-v",
        f"{project_path.resolve()}:/workspace:ro",
        "-v",
        f"{output_path.resolve()}:/evidence:rw",
        "-w",
        "/workspace",
        "--entrypoint",
        pytest_command[0],
        image,
        *pytest_command[1:],
    ]


def shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_pytest_in_docker(
    project_path: Path,
    output_dir: Path,
    command: list[str] | None = None,
    image: str = DEFAULT_IMAGE,
    timeout_seconds: int = 120,
    hash_patterns: list[str] | None = None,
    build_image: bool = True,
) -> VerificationReport:
    project_path = project_path.resolve()
    output_dir = output_dir.resolve()
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_cleanup_error = _reset_raw_dir(raw_dir)
    docker_env = os.environ.copy()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    container_name = f"pytest-evidence-{run_id}"
    command = command or DEFAULT_PYTEST_COMMAND
    started = datetime.now(timezone.utc)

    if not project_path.exists() or not project_path.is_dir():
        raise NotADirectoryError(f"project path is not a directory: {project_path}")

    docker_version = _docker_version()
    if docker_version is None:
        return _infrastructure_report(
            run_id,
            started,
            project_path,
            command,
            "missing_docker",
            "Docker CLI is not available on PATH.",
            127,
            output_dir=output_dir,
            raw_cleanup_error=raw_cleanup_error,
        )

    info = _run(["docker", "info", "--format", "{{json .}}"], timeout=15, env=docker_env)
    if info.returncode != 0 or "Cannot connect to the Docker daemon" in info.stderr:
        return _infrastructure_report(
            run_id,
            started,
            project_path,
            command,
            "docker_daemon_unavailable",
            _clean(info.stderr) or _clean(info.stdout) or "Docker daemon is unavailable.",
            127,
            docker_version=docker_version,
            output_dir=output_dir,
            raw_cleanup_error=raw_cleanup_error,
        )

    build_id = None
    if build_image and image == DEFAULT_IMAGE:
        with _docker_build_context() as build_context:
            build = _run(
                ["docker", "build", "-t", image, "."], cwd=build_context, timeout=timeout_seconds, env=docker_env
            )
            build_id = _short_sha(build.stdout + build.stderr)
            (raw_dir / "docker-build.stdout.log").write_text(build.stdout, encoding="utf-8")
            (raw_dir / "docker-build.stderr.log").write_text(build.stderr, encoding="utf-8")
            if build.returncode != 0:
                failure_kind = (
                    "docker_daemon_unavailable"
                    if "Cannot connect to the Docker daemon" in build.stderr
                    else "docker_build_failed"
                )
                return _infrastructure_report(
                    run_id,
                    started,
                    project_path,
                    command,
                    failure_kind,
                    "Docker daemon is unavailable."
                    if failure_kind == "docker_daemon_unavailable"
                    else "Docker image build failed.",
                    build.returncode,
                    docker_version=docker_version,
                    stdout=build.stdout,
                    stderr=build.stderr,
                    output_dir=output_dir,
                    raw_cleanup_error=raw_cleanup_error,
                )

    image_id = _image_id(image, docker_env)
    junit_path = raw_dir / "pytest-junit.xml"
    docker_command = build_docker_command(image, project_path, output_dir, command)
    docker_command[2:2] = ["--name", container_name]

    timed_out = False
    try:
        completed = subprocess.run(
            docker_command,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env=docker_env,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = timeout_output(exc.stdout)
        stderr = timeout_output(exc.stderr)
        stderr = (stderr + "\n" if stderr else "") + f"Docker execution timed out after {timeout_seconds} seconds."
    finally:
        cleanup = _cleanup_container(container_name, docker_env)

    (raw_dir / "docker-run.stdout.log").write_text(stdout, encoding="utf-8")
    (raw_dir / "docker-run.stderr.log").write_text(stderr, encoding="utf-8")
    (raw_dir / "docker-command.json").write_text(json.dumps(docker_command, indent=2) + "\n", encoding="utf-8")

    finished = datetime.now(timezone.utc)
    duration = round((finished - started).total_seconds(), 3)
    session, test_cases, failures = _parse_junit(junit_path, command, exit_code, started, finished)
    if timed_out:
        verdict = "error"
        failure_kind = "timeout"
        summary = f"Docker execution timed out after {timeout_seconds} seconds."
    elif exit_code == 0:
        verdict = "passed"
        failure_kind = None
        summary = "Pytest completed successfully in Docker."
    elif session and (session.failed or session.errors):
        verdict = "failed"
        failure_kind = "test_failure"
        summary = f"Pytest completed in Docker with {session.failed} failed and {session.errors} errored tests."
    else:
        verdict = "error"
        failure_kind = "runner_error"
        summary = f"Docker pytest execution failed before test results were available, exit code {exit_code}."

    infrastructure_failures: list[FailureRecord] = []
    if raw_cleanup_error:
        infrastructure_failures.append(
            FailureRecord(
                id="failure-infra-raw-cleanup",
                test_case_id=None,
                kind="raw_cleanup_failed",
                message="Could not fully clean previous raw evidence before the run.",
                details=raw_cleanup_error,
            )
        )
    if cleanup.returncode != 0:
        infrastructure_failures.append(
            FailureRecord(
                id="failure-infra-container-cleanup",
                test_case_id=None,
                kind="docker_cleanup_failed",
                message="Docker container cleanup failed after execution.",
                details=_clean(cleanup.stderr) or _clean(cleanup.stdout) or f"docker rm exited {cleanup.returncode}",
            )
        )
    if infrastructure_failures and failure_kind is None:
        verdict = "error"
        failure_kind = "runner_error"
        summary = "Pytest completed successfully, but Docker cleanup failed; captured pytest results are preserved."
    elif infrastructure_failures:
        summary = f"{summary} Additional infrastructure cleanup issue recorded."

    container = ContainerEnvironment(
        id=container_name,
        image=image,
        image_id=image_id,
        docker_version=docker_version,
        docker_build_id=build_id,
        project_mount=f"{project_path}:/workspace:ro",
        evidence_mount=f"{output_dir}:/evidence:rw",
        network_disabled=True,
        privileged=False,
        resources=RESOURCE_LIMITS,
    )
    report = VerificationReport(
        schema_version="1.0",
        run_id=run_id,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_seconds=duration,
        workdir=str(project_path),
        command=command,
        exit_code=exit_code,
        verdict=verdict,
        failure_kind=failure_kind,
        summary=summary,
        stdout=stdout,
        stderr=stderr,
        execution_mode="docker",
        file_hashes=hash_files(project_path, hash_patterns or ["**/*.py", "pyproject.toml", "pytest.ini"]),
        container=container,
        test_session=session,
        test_cases=test_cases,
        failures=[*failures, *infrastructure_failures],
        logs=[
            _log_record("log-stdout", "stdout", raw_dir / "docker-run.stdout.log", stdout),
            _log_record("log-stderr", "stderr", raw_dir / "docker-run.stderr.log", stderr),
        ],
        artifacts=_artifact_hashes(output_dir),
        reproduction=[
            f"python -m pytest_evidence_runner run --docker --project {project_path} --output-dir {output_dir}",
            shell_join(docker_command),
        ],
    )
    return report


def _docker_build_context():
    return as_file(files("pytest_evidence_runner").joinpath("docker_context"))


def _run(
    command: list[str],
    cwd: Path | None = None,
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False, env=env)
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(command, 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = timeout_output(exc.stdout)
        stderr = timeout_output(exc.stderr)
        stderr = (stderr + "\n" if stderr else "") + f"Command timed out after {timeout} seconds."
        return subprocess.CompletedProcess(command, 124, stdout, stderr)
    except subprocess.SubprocessError as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))


def _cleanup_container(container_name: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return _run(["docker", "rm", "-f", container_name], timeout=10, env=env)


def _docker_version() -> str | None:
    completed = _run(["docker", "--version"], timeout=10)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _image_id(image: str, env: dict[str, str] | None = None) -> str | None:
    completed = _run(["docker", "image", "inspect", image, "--format", "{{.Id}}"], timeout=10, env=env)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _reset_raw_dir(raw_dir: Path) -> str | None:
    errors: list[str] = []
    for path in raw_dir.iterdir():
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            errors.append(f"{path.name}: {exc}")
    return "\n".join(errors) if errors else None


def _with_junitxml(command: list[str], junit_path: str) -> list[str]:
    if any(part.startswith("--junitxml") for part in command):
        return command
    if command[:3] == ["python", "-m", "pytest"] or command[:3] == ["python3", "-m", "pytest"]:
        return [*command, f"--junitxml={junit_path}"]
    if command and Path(command[0]).name == "pytest":
        return [*command, f"--junitxml={junit_path}"]
    return command


def _parse_junit(
    path: Path,
    command: list[str],
    exit_code: int,
    started: datetime,
    finished: datetime,
) -> tuple[TestSession | None, list[TestCaseRecord], list[FailureRecord]]:
    if not path.exists():
        return None, [], []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        session = TestSession(
            id="session-pytest",
            command=command,
            status="error",
            exit_code=exit_code,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            duration_seconds=round((finished - started).total_seconds(), 3),
            total=0,
            passed=0,
            failed=0,
            errors=1,
            skipped=0,
        )
        failure = FailureRecord(
            id="failure-0001",
            test_case_id=None,
            kind="junit_parse_error",
            message=f"Could not parse pytest JUnit XML: {exc}",
            details=path.read_text(encoding="utf-8", errors="replace")[:4000],
        )
        return session, [], [failure]
    suite = root.find("testsuite") if root.tag == "testsuites" else root
    if suite is None:
        return None, [], []
    session_id = "session-pytest"
    test_cases: list[TestCaseRecord] = []
    failures: list[FailureRecord] = []
    for index, node in enumerate(suite.findall(".//testcase"), start=1):
        classname = node.attrib.get("classname", "")
        name = node.attrib.get("name", f"test_{index}")
        case_id = _stable_test_id(classname, name)
        failure_ids: list[str] = []
        status = "passed"
        for child in list(node):
            if child.tag not in {"failure", "error", "skipped"}:
                continue
            if child.tag == "skipped":
                status = "skipped"
                continue
            status = "failed" if child.tag == "failure" else "error"
            failure_id = f"failure-{len(failures) + 1:04d}"
            failure_ids.append(failure_id)
            failures.append(
                FailureRecord(
                    id=failure_id,
                    test_case_id=case_id,
                    kind=child.tag,
                    message=child.attrib.get("message", ""),
                    details=child.text or "",
                )
            )
        test_cases.append(
            TestCaseRecord(
                id=case_id,
                session_id=session_id,
                name=name,
                classname=classname,
                status=status,
                duration_seconds=float(node.attrib.get("time", "0") or 0),
                stdout=(node.findtext("system-out") or ""),
                stderr=(node.findtext("system-err") or ""),
                failure_ids=failure_ids,
            )
        )
    total = int(suite.attrib.get("tests", len(test_cases)) or len(test_cases))
    failed = int(suite.attrib.get("failures", "0") or 0)
    errors = int(suite.attrib.get("errors", "0") or 0)
    skipped = int(suite.attrib.get("skipped", "0") or 0)
    passed = max(total - failed - errors - skipped, 0)
    status = "passed" if exit_code == 0 else ("failed" if failed or errors else "error")
    session = TestSession(
        id=session_id,
        command=command,
        status=status,
        exit_code=exit_code,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_seconds=round((finished - started).total_seconds(), 3),
        total=total,
        passed=passed,
        failed=failed,
        errors=errors,
        skipped=skipped,
        test_case_ids=[case.id for case in test_cases],
    )
    return session, test_cases, failures


def _artifact_hashes(output_dir: Path) -> list[FileHash]:
    items: list[FileHash] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"report.json", "report.md"}:
            continue
        relative = path.relative_to(output_dir).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        items.append(FileHash(path=relative, sha256=digest, size_bytes=path.stat().st_size))
    return items


def _stable_test_id(classname: str, name: str) -> str:
    label = f"{classname}::{name}"
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:16]
    return f"test-{digest}"


def _log_record(log_id: str, stream: str, path: Path, content: str) -> EvidenceLog:
    encoded = content.encode("utf-8")
    return EvidenceLog(
        id=log_id,
        stream=stream,
        path=path.name,
        sha256=hashlib.sha256(encoded).hexdigest(),
        size_bytes=len(encoded),
        content=content,
    )


def _infrastructure_report(
    run_id: str,
    started: datetime,
    project_path: Path,
    command: list[str],
    failure_kind: str,
    summary: str,
    exit_code: int,
    docker_version: str | None = None,
    stdout: str = "",
    stderr: str = "",
    output_dir: Path | None = None,
    raw_cleanup_error: str | None = None,
) -> VerificationReport:
    finished = datetime.now(timezone.utc)
    failures = []
    if raw_cleanup_error:
        failures.append(
            FailureRecord(
                id="failure-infra-raw-cleanup",
                test_case_id=None,
                kind="raw_cleanup_failed",
                message="Could not fully clean previous raw evidence before the run.",
                details=raw_cleanup_error,
            )
        )
    return VerificationReport(
        schema_version="1.0",
        run_id=run_id,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_seconds=round((finished - started).total_seconds(), 3),
        workdir=str(project_path),
        command=command,
        exit_code=exit_code,
        verdict="error",
        failure_kind=failure_kind,
        summary=summary,
        stdout=stdout,
        stderr=stderr,
        execution_mode="docker",
        artifacts=_artifact_hashes(output_dir) if output_dir else [],
        failures=failures,
        container=ContainerEnvironment(
            id="not-created",
            image=DEFAULT_IMAGE,
            image_id=None,
            docker_version=docker_version or "unavailable",
            docker_build_id=None,
            project_mount=f"{project_path}:/workspace:ro",
            evidence_mount="not-created",
            network_disabled=True,
            privileged=False,
            resources=RESOURCE_LIMITS,
        ),
    )


def _short_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _clean(value: str) -> str:
    return value.strip()
