from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FAILED_STATUSES = {"failed", "error"}


@dataclass(frozen=True)
class Thresholds:
    absolute_seconds: float = 0.25
    relative_percent: float = 50.0


def save_baseline(name: str, report_path: Path, baseline_dir: Path) -> tuple[Path, Path]:
    if not name or any(part in name for part in ("/", "\\", "..")):
        raise ValueError("baseline name must be a simple path segment")
    report = load_report(report_path)
    validate_report(report)
    target_dir = baseline_dir / name
    target_dir.mkdir(parents=True, exist_ok=True)
    copied = target_dir / "report.json"
    shutil.copyfile(report_path, copied)
    metadata = {
        "schema_version": "1.0",
        "name": name,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(report_path),
        "copied_report": "report.json",
        "source_run_id": report.get("run_id"),
        "source_verdict": report.get("verdict"),
    }
    metadata_path = target_dir / "baseline.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return copied, metadata_path


def compare_reports(
    baseline_path: Path,
    current_path: Path,
    output_dir: Path,
    thresholds: Thresholds | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    thresholds = thresholds or Thresholds()
    baseline = load_report(baseline_path)
    current = load_report(current_path)
    validate_report(baseline)
    validate_report(current)
    comparison = build_comparison(
        baseline,
        current,
        baseline_path=baseline_path,
        current_path=current_path,
        thresholds=thresholds,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "comparison.json"
    md_path = output_dir / "comparison.md"
    json_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_comparison_markdown(comparison), encoding="utf-8")
    return comparison, json_path, md_path


def load_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON evidence report: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"evidence report must be a JSON object: {path}")
    return data


def validate_report(report: dict[str, Any]) -> None:
    required = {"schema_version", "run_id", "verdict", "test_cases"}
    missing = sorted(required - set(report))
    if missing:
        raise ValueError(f"evidence report missing required fields: {', '.join(missing)}")
    if not isinstance(report.get("test_cases"), list):
        raise ValueError("evidence report field test_cases must be a list")
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in report["test_cases"]:
        if not isinstance(item, dict):
            raise ValueError("test_cases entries must be objects")
        test_id = item.get("id")
        if not isinstance(test_id, str) or not test_id:
            raise ValueError("each test case must have a non-empty string id")
        if test_id in seen:
            duplicates.append(test_id)
        seen.add(test_id)
    if duplicates:
        raise ValueError(f"duplicate test identifiers: {', '.join(sorted(set(duplicates)))}")


def build_comparison(
    baseline: dict[str, Any],
    current: dict[str, Any],
    baseline_path: Path,
    current_path: Path,
    thresholds: Thresholds,
) -> dict[str, Any]:
    baseline_cases = {item["id"]: item for item in baseline.get("test_cases", [])}
    current_cases = {item["id"]: item for item in current.get("test_cases", [])}
    all_ids = sorted(set(baseline_cases) | set(current_cases))
    transitions = [
        _transition(test_id, baseline_cases.get(test_id), current_cases.get(test_id), thresholds) for test_id in all_ids
    ]
    counts: dict[str, int] = {
        "regression": 0,
        "fixed": 0,
        "persistent_failure": 0,
        "unchanged_passing": 0,
        "added": 0,
        "removed": 0,
        "other_change": 0,
    }
    performance_counts = {"slower": 0, "faster": 0, "unchanged": 0, "not_comparable": 0}
    for item in transitions:
        counts[item["classification"]] = counts.get(item["classification"], 0) + 1
        perf = item["performance"]["classification"]
        performance_counts[perf] = performance_counts.get(perf, 0) + 1

    introduced_regressions = counts["regression"] > 0
    comparison_id = (
        f"cmp-{_short_hash(str(baseline_path) + str(current_path) + datetime.now(timezone.utc).isoformat())}"
    )
    return {
        "schema_version": "1.0",
        "comparison_id": comparison_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "baseline": _run_ref(baseline, baseline_path),
        "current": _run_ref(current, current_path),
        "thresholds": {
            "absolute_seconds": thresholds.absolute_seconds,
            "relative_percent": thresholds.relative_percent,
        },
        "summary": {
            "introduced_regressions": introduced_regressions,
            "verdict": "regression" if introduced_regressions else "no_regression",
            "counts": counts,
            "performance_counts": performance_counts,
            "baseline_verdict": baseline.get("verdict"),
            "current_verdict": current.get("verdict"),
        },
        "transitions": transitions,
        "source_evidence": {
            "baseline_report": str(baseline_path),
            "current_report": str(current_path),
        },
    }


def render_comparison_markdown(comparison: dict[str, Any]) -> str:
    summary = comparison["summary"]
    counts = summary["counts"]
    perf_counts = summary["performance_counts"]
    regression_note = (
        "The current run introduced regressions."
        if summary["introduced_regressions"]
        else "No passed-to-failed regressions were detected."
    )
    rows = "\n".join(
        "| `{test_id}` | {name} | {before} | {after} | {classification} | {duration} |".format(
            test_id=item["test_id"],
            name=item["name"],
            before=item["baseline_status"] or "missing",
            after=item["current_status"] or "missing",
            classification=item["classification"],
            duration=_duration_label(item),
        )
        for item in comparison["transitions"]
    )
    if not rows:
        rows = "| _(none)_ | | | | | |"

    details = "\n\n".join(_transition_detail(item) for item in comparison["transitions"])
    if not details:
        details = "- No individual transitions."

    return f"""# Evidence Comparison Report

**Verdict:** {summary["verdict"]}

**Summary:** {regression_note}

## Runs

- Baseline: `{comparison["baseline"]["run_id"]}` `{summary["baseline_verdict"]}` from `{comparison["baseline"]["report_path"]}`
- Current: `{comparison["current"]["run_id"]}` `{summary["current_verdict"]}` from `{comparison["current"]["report_path"]}`

## Transition Counts

- Regressions: `{counts["regression"]}`
- Fixed: `{counts["fixed"]}`
- Persistent failures: `{counts["persistent_failure"]}`
- Unchanged passing: `{counts["unchanged_passing"]}`
- Added: `{counts["added"]}`
- Removed: `{counts["removed"]}`
- Other changes: `{counts["other_change"]}`

## Performance Counts

- Slower: `{perf_counts["slower"]}`
- Faster: `{perf_counts["faster"]}`
- Unchanged: `{perf_counts["unchanged"]}`
- Not comparable: `{perf_counts["not_comparable"]}`

## Individual Test Transitions

| Test id | Test | Baseline | Current | Classification | Duration delta |
| --- | --- | --- | --- | --- | --- |
{rows}

## Evidence Links

{details}
"""


def _transition(
    test_id: str,
    baseline: dict[str, Any] | None,
    current: dict[str, Any] | None,
    thresholds: Thresholds,
) -> dict[str, Any]:
    before = baseline.get("status") if baseline else None
    after = current.get("status") if current else None
    if baseline is None:
        classification = "added"
    elif current is None:
        classification = "removed"
    elif before == "passed" and after in FAILED_STATUSES:
        classification = "regression"
    elif before in FAILED_STATUSES and after == "passed":
        classification = "fixed"
    elif before in FAILED_STATUSES and after in FAILED_STATUSES:
        classification = "persistent_failure"
    elif before == "passed" and after == "passed":
        classification = "unchanged_passing"
    else:
        classification = "other_change"
    return {
        "test_id": test_id,
        "name": _case_label(current or baseline or {}),
        "baseline_status": before,
        "current_status": after,
        "classification": classification,
        "performance": _performance(baseline, current, thresholds),
        "baseline_source": _case_source(baseline),
        "current_source": _case_source(current),
    }


def _performance(
    baseline: dict[str, Any] | None,
    current: dict[str, Any] | None,
    thresholds: Thresholds,
) -> dict[str, Any]:
    if baseline is None or current is None:
        return {"classification": "not_comparable", "baseline_seconds": None, "current_seconds": None}
    before = float(baseline.get("duration_seconds", 0) or 0)
    after = float(current.get("duration_seconds", 0) or 0)
    delta = round(after - before, 6)
    percent = None if before == 0 else round((delta / before) * 100, 2)
    meaningful = abs(delta) >= thresholds.absolute_seconds
    if percent is not None:
        meaningful = meaningful or abs(percent) >= thresholds.relative_percent
    if not meaningful:
        classification = "unchanged"
    elif delta > 0:
        classification = "slower"
    else:
        classification = "faster"
    return {
        "classification": classification,
        "baseline_seconds": before,
        "current_seconds": after,
        "delta_seconds": delta,
        "delta_percent": percent,
    }


def _case_source(case: dict[str, Any] | None) -> dict[str, Any] | None:
    if case is None:
        return None
    return {
        "test_case_id": case.get("id"),
        "session_id": case.get("session_id"),
        "failure_ids": case.get("failure_ids", []),
        "stdout_present": bool(case.get("stdout")),
        "stderr_present": bool(case.get("stderr")),
    }


def _run_ref(report: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "run_id": report.get("run_id"),
        "verdict": report.get("verdict"),
        "failure_kind": report.get("failure_kind"),
        "report_path": str(path),
        "logs": [
            {"id": item.get("id"), "path": item.get("path"), "sha256": item.get("sha256")}
            for item in report.get("logs", [])
        ],
        "artifacts": [{"path": item.get("path"), "sha256": item.get("sha256")} for item in report.get("artifacts", [])],
    }


def _case_label(case: dict[str, Any]) -> str:
    classname = case.get("classname", "")
    name = case.get("name", "")
    return f"{classname}.{name}".strip(".")


def _duration_label(item: dict[str, Any]) -> str:
    perf = item["performance"]
    if perf["classification"] == "not_comparable":
        return "n/a"
    return f"{perf['delta_seconds']:+.6f}s ({perf['classification']})"


def _transition_detail(item: dict[str, Any]) -> str:
    return (
        f"### `{item['test_id']}` {item['name']}\n\n"
        f"- Classification: `{item['classification']}`\n"
        f"- Baseline source: `{json.dumps(item['baseline_source'], sort_keys=True)}`\n"
        f"- Current source: `{json.dumps(item['current_source'], sort_keys=True)}`\n"
        f"- Performance: `{json.dumps(item['performance'], sort_keys=True)}`"
    )


def _short_hash(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
