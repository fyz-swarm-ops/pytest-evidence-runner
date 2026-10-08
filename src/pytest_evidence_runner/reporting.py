from __future__ import annotations

import json
from pathlib import Path

from .models import VerificationReport


def write_reports(report: VerificationReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    md_path = output_dir / "report.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def render_markdown(report: VerificationReport) -> str:
    command = " ".join(report.command)
    hashes = "\n".join(
        f"- `{item.path}` `{item.sha256}` ({item.size_bytes} bytes)" for item in report.file_hashes
    )
    if not hashes:
        hashes = "- No file hashes requested."

    stdout = _fence(report.stdout)
    stderr = _fence(report.stderr)
    session = _render_session(report)
    failures = _render_failures(report)
    container = _render_container(report)
    artifacts = _render_artifacts(report)
    reproduction = "\n".join(f"- `{item}`" for item in report.reproduction) or "- See command above."
    return f"""# Verification Report

**Verdict:** {report.verdict}

**Summary:** {report.summary}

**Failure kind:** {report.failure_kind or "none"}

## Run

- Run id: `{report.run_id}`
- Execution mode: `{report.execution_mode}`
- Started: `{report.started_at}`
- Finished: `{report.finished_at}`
- Duration: `{report.duration_seconds}` seconds
- Working directory: `{report.workdir}`
- Command: `{command}`
- Exit code: `{report.exit_code}`

{container}

{session}

{failures}

## Evidence Hashes

{hashes}

## Artifacts

{artifacts}

## Stdout

{stdout}

## Stderr

{stderr}

## Reproduce

{reproduction}
"""


def _fence(value: str) -> str:
    if not value:
        return "```text\n\n```"
    return "```text\n" + value.rstrip() + "\n```"


def _render_container(report: VerificationReport) -> str:
    if report.container is None:
        return "## Container\n\n- Not used."
    container = report.container
    resources = ", ".join(f"{key}={value}" for key, value in container.resources.items())
    return f"""## Container

- Container id/name: `{container.id}`
- Image: `{container.image}`
- Image id: `{container.image_id or "unknown"}`
- Docker: `{container.docker_version}`
- Network disabled: `{container.network_disabled}`
- Privileged: `{container.privileged}`
- Resources: `{resources}`
- Project mount: `{container.project_mount}`
- Evidence mount: `{container.evidence_mount}`"""


def _render_session(report: VerificationReport) -> str:
    if report.test_session is None:
        return "## Test Session\n\n- No structured test session was captured."
    session = report.test_session
    rows = [
        f"- Status: `{session.status}`",
        f"- Total: `{session.total}`",
        f"- Passed: `{session.passed}`",
        f"- Failed: `{session.failed}`",
        f"- Errors: `{session.errors}`",
        f"- Skipped: `{session.skipped}`",
    ]
    cases = "\n".join(
        f"- `{case.id}` `{case.status}` `{case.classname}.{case.name}` ({case.duration_seconds}s)"
        for case in report.test_cases
    )
    if not cases:
        cases = "- No individual test cases captured."
    return "## Test Session\n\n" + "\n".join(rows) + "\n\n### Test Cases\n\n" + cases


def _render_failures(report: VerificationReport) -> str:
    if not report.failures:
        return "## Failures\n\n- No structured failures captured."
    blocks = []
    by_id = {case.id: case for case in report.test_cases}
    for failure in report.failures:
        case = by_id.get(failure.test_case_id or "")
        label = f"{case.classname}.{case.name}" if case else "runner"
        blocks.append(
            f"### `{failure.id}` `{failure.kind}` in `{label}`\n\n"
            f"Message: {failure.message or '(none)'}\n\n"
            f"{_fence(failure.details)}"
        )
    return "## Failures\n\n" + "\n\n".join(blocks)


def _render_artifacts(report: VerificationReport) -> str:
    if not report.artifacts:
        return "- No raw artifacts captured."
    return "\n".join(
        f"- `{item.path}` `{item.sha256}` ({item.size_bytes} bytes)" for item in report.artifacts
    )
