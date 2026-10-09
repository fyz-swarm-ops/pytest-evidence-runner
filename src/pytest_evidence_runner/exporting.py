from __future__ import annotations

import html
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .comparison import load_report, render_comparison_markdown
from .hashing import sha256_file


class ZipValidationError(ValueError):
    pass


def export_run(source_dir: Path, formats: set[str], output_dir: Path) -> list[Path]:
    report_path = source_dir / "report.json"
    report = load_report(report_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "run-report"
    outputs = _write_common(report, "run", stem, formats, output_dir)
    if "zip" in formats:
        outputs.append(_write_zip(output_dir / "run-evidence-package.zip", source_dir, outputs, "run", report))
    return outputs


def export_comparison(source_dir: Path, formats: set[str], output_dir: Path) -> list[Path]:
    comparison_path = source_dir / "comparison.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "comparison-report"
    outputs = _write_common(comparison, "comparison", stem, formats, output_dir)
    if "zip" in formats:
        outputs.append(
            _write_zip(output_dir / "comparison-evidence-package.zip", source_dir, outputs, "comparison", comparison)
        )
    return outputs


def _write_common(
    data: dict[str, Any],
    kind: str,
    stem: str,
    formats: set[str],
    output_dir: Path,
) -> list[Path]:
    outputs: list[Path] = []
    if "json" in formats:
        path = output_dir / f"{stem}.json"
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        outputs.append(path)
    if "md" in formats:
        path = output_dir / f"{stem}.md"
        path.write_text(_markdown(data, kind), encoding="utf-8")
        outputs.append(path)
    if "html" in formats:
        path = output_dir / f"{stem}.html"
        path.write_text(_html(data, kind), encoding="utf-8")
        outputs.append(path)
    if "pdf" in formats:
        path = output_dir / f"{stem}.pdf"
        _write_simple_pdf(path, _pdf_lines(data, kind))
        outputs.append(path)
    return outputs


def _markdown(data: dict[str, Any], kind: str) -> str:
    if kind == "comparison":
        return render_comparison_markdown(data)
    return _run_markdown(data)


def _run_markdown(data: dict[str, Any]) -> str:
    session = data.get("test_session") or {}
    cases = (
        "\n".join(
            f"- `{item.get('id')}` `{item.get('status')}` `{item.get('classname')}.{item.get('name')}` ({item.get('duration_seconds')}s)"
            for item in data.get("test_cases", [])
        )
        or "- No structured test cases captured."
    )
    failures = (
        "\n\n".join(
            f"### `{item.get('id')}` `{item.get('kind')}`\n\n"
            f"Message: {item.get('message') or '(none)'}\n\n"
            f"```text\n{item.get('details') or ''}\n```"
            for item in data.get("failures", [])
        )
        or "- No structured failures captured."
    )
    artifacts = (
        "\n".join(
            f"- `{item.get('path')}` `{item.get('sha256')}` ({item.get('size_bytes')} bytes)"
            for item in data.get("artifacts", [])
        )
        or "- No artifacts captured."
    )
    reproduction = (
        "\n".join(f"- `{item}`" for item in data.get("reproduction", [])) or "- No reproduction command captured."
    )
    return f"""# Verification Report

**Verdict:** {data.get("verdict")}

**Summary:** {data.get("summary", "")}

## Run

- Run id: `{data.get("run_id")}`
- Execution mode: `{data.get("execution_mode")}`
- Exit code: `{data.get("exit_code")}`
- Duration: `{data.get("duration_seconds")}` seconds
- Tests: `{session.get("total", 0)}` total, `{session.get("passed", 0)}` passed, `{session.get("failed", 0)}` failed, `{session.get("errors", 0)}` errors

## Test Cases

{cases}

## Failures

{failures}

## Artifacts

{artifacts}

## Reproduce

{reproduction}
"""


def _html(data: dict[str, Any], kind: str) -> str:
    title = "Evidence Comparison Report" if kind == "comparison" else "Verification Report"
    body = _comparison_html(data) if kind == "comparison" else _run_html(data)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 2rem; line-height: 1.45; color: #202124; }}
code, pre {{ background: #f5f7fa; border-radius: 4px; }}
pre {{ padding: 1rem; overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
th, td {{ border: 1px solid #d0d7de; padding: 0.45rem; text-align: left; vertical-align: top; }}
th {{ background: #f6f8fa; }}
details {{ border: 1px solid #d0d7de; border-radius: 6px; margin: 0.75rem 0; padding: 0.5rem 0.75rem; }}
summary {{ cursor: pointer; font-weight: 650; }}
.verdict {{ font-size: 1.15rem; font-weight: 700; }}
.bad {{ color: #b42318; }}
.good {{ color: #067647; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _run_html(data: dict[str, Any]) -> str:
    cases = (
        "\n".join(
            f"<details><summary><code>{html.escape(case['id'])}</code> {html.escape(case.get('status', ''))} {html.escape(case.get('classname', ''))}.{html.escape(case.get('name', ''))}</summary>"
            f"<p>Duration: {case.get('duration_seconds')} seconds</p>"
            f"<p>Failures: {html.escape(', '.join(case.get('failure_ids', [])) or 'none')}</p>"
            f"<pre>{html.escape(case.get('stdout', '') or '')}</pre>"
            f"</details>"
            for case in data.get("test_cases", [])
        )
        or "<p>No structured test cases captured.</p>"
    )
    failures = (
        "\n".join(
            f"<details open><summary><code>{html.escape(item['id'])}</code> {html.escape(item.get('kind', ''))}</summary>"
            f"<p>{html.escape(item.get('message', '') or '(no message)')}</p>"
            f"<pre>{html.escape(item.get('details', '') or '')}</pre></details>"
            for item in data.get("failures", [])
        )
        or "<p>No structured failures captured.</p>"
    )
    session = data.get("test_session") or {}
    return f"""<h1>Verification Report</h1>
<p class="verdict">Verdict: <span class="{_verdict_class(data.get("verdict"))}">{html.escape(str(data.get("verdict")))}</span></p>
<p>{html.escape(str(data.get("summary", "")))}</p>
<h2>Executive Summary</h2>
<table><tr><th>Run id</th><td>{html.escape(str(data.get("run_id")))}</td></tr>
<tr><th>Execution mode</th><td>{html.escape(str(data.get("execution_mode")))}</td></tr>
<tr><th>Exit code</th><td>{html.escape(str(data.get("exit_code")))}</td></tr>
<tr><th>Tests</th><td>{session.get("total", 0)} total, {session.get("passed", 0)} passed, {session.get("failed", 0)} failed, {session.get("errors", 0)} errors</td></tr></table>
<h2>Test Cases</h2>
{cases}
<h2>Failures</h2>
{failures}
<h2>Evidence References</h2>
<pre>{html.escape(json.dumps({"logs": data.get("logs", []), "artifacts": data.get("artifacts", []), "reproduction": data.get("reproduction", [])}, indent=2))}</pre>"""


def _comparison_html(data: dict[str, Any]) -> str:
    summary = data["summary"]
    rows = "\n".join(
        f"<tr><td><code>{html.escape(item['test_id'])}</code></td><td>{html.escape(item['name'])}</td>"
        f"<td>{html.escape(str(item.get('baseline_status') or 'missing'))}</td>"
        f"<td>{html.escape(str(item.get('current_status') or 'missing'))}</td>"
        f"<td>{html.escape(item['classification'])}</td>"
        f"<td>{html.escape(item['performance']['classification'])}</td></tr>"
        for item in data.get("transitions", [])
    )
    details = "\n".join(
        f"<details><summary><code>{html.escape(item['test_id'])}</code> {html.escape(item['classification'])}</summary>"
        f"<pre>{html.escape(json.dumps(item, indent=2, sort_keys=True))}</pre></details>"
        for item in data.get("transitions", [])
    )
    return f"""<h1>Evidence Comparison Report</h1>
<p class="verdict">Verdict: <span class="{_verdict_class(summary.get("verdict"))}">{html.escape(summary.get("verdict", ""))}</span></p>
<h2>Executive Summary</h2>
<table><tr><th>Baseline</th><td>{html.escape(str(data["baseline"]["run_id"]))} ({html.escape(str(summary["baseline_verdict"]))})</td></tr>
<tr><th>Current</th><td>{html.escape(str(data["current"]["run_id"]))} ({html.escape(str(summary["current_verdict"]))})</td></tr>
<tr><th>Regressions</th><td>{summary["counts"]["regression"]}</td></tr>
<tr><th>Fixes</th><td>{summary["counts"]["fixed"]}</td></tr>
<tr><th>Persistent failures</th><td>{summary["counts"]["persistent_failure"]}</td></tr></table>
<h2>Transitions</h2>
<table><tr><th>Test id</th><th>Test</th><th>Baseline</th><th>Current</th><th>Transition</th><th>Performance</th></tr>{rows}</table>
<h2>Drilldown</h2>
{details}"""


def _verdict_class(value: Any) -> str:
    return "bad" if value in {"failed", "error", "regression"} else "good"


def _pdf_lines(data: dict[str, Any], kind: str) -> list[str]:
    if kind == "comparison":
        summary = data["summary"]
        counts = summary["counts"]
        lines = [
            "Evidence Comparison Report",
            f"Verdict: {summary['verdict']}",
            f"Baseline: {data['baseline']['run_id']} {summary['baseline_verdict']}",
            f"Current: {data['current']['run_id']} {summary['current_verdict']}",
            f"Regressions: {counts['regression']}  Fixes: {counts['fixed']}  Persistent failures: {counts['persistent_failure']}",
            f"Added: {counts['added']}  Removed: {counts['removed']}  Unchanged passing: {counts['unchanged_passing']}",
            "",
            "Detailed findings:",
        ]
        for item in data.get("transitions", [])[:35]:
            lines.append(
                f"- {item['classification']}: {item['name']} ({item['baseline_status']} -> {item['current_status']})"
            )
        return lines
    session = data.get("test_session") or {}
    lines = [
        "Verification Report",
        f"Verdict: {data.get('verdict')}",
        f"Run id: {data.get('run_id')}",
        f"Execution mode: {data.get('execution_mode')}",
        f"Exit code: {data.get('exit_code')}",
        f"Tests: {session.get('total', 0)} total, {session.get('passed', 0)} passed, {session.get('failed', 0)} failed, {session.get('errors', 0)} errors",
        "",
        "Detailed findings:",
    ]
    for item in data.get("test_cases", [])[:35]:
        lines.append(
            f"- {item.get('status')}: {item.get('classname')}.{item.get('name')} ({item.get('duration_seconds')}s)"
        )
    return lines


def _write_simple_pdf(path: Path, lines: list[str]) -> None:
    # Small dependency-free PDF writer for portable text reports. It intentionally
    # emits simple single-page text; HTML/Markdown carry the richer drilldown.
    escaped = [_pdf_escape(line[:120]) for line in lines]
    text_ops = ["BT", "/F1 11 Tf", "50 770 Td"]
    first = True
    for line in escaped:
        if not first:
            text_ops.append("0 -16 Td")
        first = False
        text_ops.append(f"({line}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    path.write_bytes(bytes(content))


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_zip(path: Path, source_dir: Path, report_paths: list[Path], kind: str, data: dict[str, Any]) -> Path:
    manifest = {
        "schema_version": "1.0",
        "kind": kind,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "SHA-256 hashes provide tamper evidence for package contents; they are not a cryptographic signature.",
        "metadata": {
            "run_id": data.get("run_id"),
            "comparison_id": data.get("comparison_id"),
            "verdict": data.get("verdict") or data.get("summary", {}).get("verdict"),
        },
        "files": [],
    }
    manifest_path = path.with_suffix(".manifest.json")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if source_dir.exists():
            for item in sorted(source_dir.rglob("*")):
                if item.is_file():
                    arcname = f"evidence/{item.relative_to(source_dir).as_posix()}"
                    zf.write(item, arcname)
                    manifest["files"].append(_manifest_entry(item, arcname))
        for item in report_paths:
            if item.exists():
                arcname = f"reports/{item.name}"
                zf.write(item, arcname)
                manifest["files"].append(_manifest_entry(item, arcname))
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        zf.write(manifest_path, "manifest.json")
    manifest_path.unlink(missing_ok=True)
    validate_evidence_zip(path)
    return path


def _manifest_entry(path: Path, arcname: str) -> dict[str, Any]:
    return {
        "path": arcname,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def validate_evidence_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as zf:
        try:
            manifest = json.loads(zf.read("manifest.json"))
        except KeyError as exc:
            raise ZipValidationError(f"{path} is missing manifest.json") from exc
        names = set(zf.namelist())
        problems: list[str] = []
        manifest_paths = {entry.get("path") for entry in manifest.get("files", [])}
        extra_members = names - {"manifest.json"} - manifest_paths
        for member in sorted(extra_members):
            problems.append(f"{member}: missing from manifest")
        for entry in manifest.get("files", []):
            member = entry.get("path")
            if member not in names:
                problems.append(f"{member}: missing from ZIP")
                continue
            data = zf.read(member)
            actual_sha = hashlib.sha256(data).hexdigest()
            actual_size = len(data)
            if actual_sha != entry.get("sha256") or actual_size != entry.get("size_bytes"):
                problems.append(f"{member}: manifest hash/size mismatch")
        if problems:
            raise ZipValidationError(f"{path} failed integrity validation: {'; '.join(problems)}")
