import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pytest_evidence_runner.comparison import Thresholds, compare_reports, save_baseline, validate_report
from pytest_evidence_runner.exporting import export_comparison, export_run


def report(run_id, verdict, cases):
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "duration_seconds": 1,
        "workdir": "/workspace",
        "command": ["python", "-m", "pytest"],
        "exit_code": 0 if verdict == "passed" else 1,
        "verdict": verdict,
        "failure_kind": None if verdict == "passed" else "test_failure",
        "summary": "sample",
        "stdout": "",
        "stderr": "",
        "execution_mode": "docker",
        "test_session": {"total": len(cases), "passed": 0, "failed": 0, "errors": 0, "skipped": 0},
        "test_cases": [
            {
                "id": test_id,
                "session_id": "session-pytest",
                "classname": "tests.test_sample",
                "name": test_id,
                "status": status,
                "duration_seconds": duration,
                "stdout": "",
                "stderr": "",
                "failure_ids": [f"failure-{test_id}"] if status in {"failed", "error"} else [],
            }
            for test_id, status, duration in cases
        ],
        "failures": [],
        "logs": [{"id": "log-stdout", "path": "docker-run.stdout.log", "sha256": "abc"}],
        "artifacts": [{"path": "raw/pytest-junit.xml", "sha256": "def", "size_bytes": 10}],
        "reproduction": ["python -m pytest_evidence_runner run --docker --project sample"],
    }


class ComparisonExportingTests(unittest.TestCase):
    def test_transition_categories_and_performance(self):
        baseline = report(
            "base",
            "failed",
            [
                ("regression", "passed", 0.1),
                ("fixed", "failed", 0.2),
                ("persistent", "error", 0.3),
                ("unchanged", "passed", 0.1),
                ("removed", "passed", 0.1),
                ("slow", "passed", 0.1),
            ],
        )
        current = report(
            "current",
            "failed",
            [
                ("regression", "failed", 0.1),
                ("fixed", "passed", 0.2),
                ("persistent", "failed", 0.3),
                ("unchanged", "passed", 0.1),
                ("added", "passed", 0.1),
                ("slow", "passed", 0.5),
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base_path = tmp_path / "base.json"
            current_path = tmp_path / "current.json"
            base_path.write_text(json.dumps(baseline), encoding="utf-8")
            current_path.write_text(json.dumps(current), encoding="utf-8")
            comparison, json_path, md_path = compare_reports(
                base_path,
                current_path,
                tmp_path / "comparison",
                Thresholds(absolute_seconds=0.25, relative_percent=50),
            )
            counts = comparison["summary"]["counts"]
            self.assertEqual(counts["regression"], 1)
            self.assertEqual(counts["fixed"], 1)
            self.assertEqual(counts["persistent_failure"], 1)
            self.assertEqual(counts["unchanged_passing"], 2)
            self.assertEqual(counts["added"], 1)
            self.assertEqual(counts["removed"], 1)
            self.assertEqual(comparison["summary"]["performance_counts"]["slower"], 1)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

    def test_duplicate_test_identifiers_rejected(self):
        data = report("dup", "passed", [("same", "passed", 0.1), ("same", "passed", 0.2)])
        with self.assertRaisesRegex(ValueError, "duplicate test identifiers"):
            validate_report(data)

    def test_malformed_report_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            validate_report({"schema_version": "1.0"})

    def test_baseline_save_and_exports(self):
        data = report("run", "passed", [("one", "passed", 0.1)])
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            run_dir = tmp_path / "run"
            run_dir.mkdir()
            report_path = run_dir / "report.json"
            report_path.write_text(json.dumps(data), encoding="utf-8")
            (run_dir / "report.md").write_text("# Verification Report\n", encoding="utf-8")
            copied, metadata = save_baseline("v1", report_path, tmp_path / "baselines")
            self.assertTrue(copied.exists())
            self.assertTrue(metadata.exists())
            outputs = export_run(run_dir, {"json", "md", "html", "pdf", "zip"}, tmp_path / "exports")
            suffixes = {item.suffix for item in outputs}
            self.assertIn(".html", suffixes)
            self.assertIn(".pdf", suffixes)
            zip_path = [item for item in outputs if item.suffix == ".zip"][0]
            with zipfile.ZipFile(zip_path) as zf:
                self.assertIn("manifest.json", zf.namelist())
                self.assertIn("evidence/report.json", zf.namelist())

    def test_comparison_export_zip(self):
        comparison = {
            "schema_version": "1.0",
            "comparison_id": "cmp",
            "summary": {
                "verdict": "no_regression",
                "introduced_regressions": False,
                "baseline_verdict": "passed",
                "current_verdict": "passed",
                "counts": {
                    "regression": 0,
                    "fixed": 0,
                    "persistent_failure": 0,
                    "unchanged_passing": 1,
                    "added": 0,
                    "removed": 0,
                    "other_change": 0,
                },
                "performance_counts": {"slower": 0, "faster": 0, "unchanged": 1, "not_comparable": 0},
            },
            "baseline": {"run_id": "base"},
            "current": {"run_id": "current"},
            "transitions": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            comp_dir = Path(tmp) / "comparison"
            comp_dir.mkdir()
            (comp_dir / "comparison.json").write_text(json.dumps(comparison), encoding="utf-8")
            outputs = export_comparison(comp_dir, {"html", "pdf", "zip"}, Path(tmp) / "exports")
            self.assertTrue(any(item.name == "comparison-report.html" for item in outputs))
            self.assertTrue(any(item.name == "comparison-evidence-package.zip" for item in outputs))


if __name__ == "__main__":
    unittest.main()
