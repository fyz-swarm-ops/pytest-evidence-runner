import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pytest_evidence_runner.docker import build_docker_command, shell_join
from pytest_evidence_runner.reporting import render_markdown, write_reports
from pytest_evidence_runner.runner import run_verification


SAMPLE = ROOT / "samples" / "unittest_project"


class RunnerTests(unittest.TestCase):
    def test_successful_run_writes_evidence(self):
        report = run_verification(
            ["python3", "-m", "unittest", "discover", "-s", "tests"],
            SAMPLE,
            ["app/**/*.py"],
        )
        self.assertEqual(report.verdict, "passed")
        self.assertEqual(report.exit_code, 0)
        self.assertEqual(report.execution_mode, "local")
        self.assertTrue(report.run_id.startswith("run-"))
        self.assertGreaterEqual(len(report.file_hashes), 1)
        markdown = render_markdown(report)
        self.assertIn("Verification Report", markdown)
        self.assertIn("passed", markdown)

    def test_failed_run_is_classified(self):
        report = run_verification(["python3", "-c", "raise SystemExit(7)"], SAMPLE)
        self.assertEqual(report.verdict, "failed")
        self.assertEqual(report.exit_code, 7)

    def test_write_reports(self):
        report = run_verification(["python3", "-c", "print('ok')"], SAMPLE)
        with tempfile.TemporaryDirectory() as tmp:
            json_path, md_path = write_reports(report, Path(tmp))
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            data = json.loads(json_path.read_text())
            self.assertEqual(data["verdict"], "passed")

    def test_docker_command_rendering(self):
        command = build_docker_command(
            "python:3.12-slim",
            SAMPLE,
            ROOT / "evidence",
            ["python3", "-m", "unittest"],
        )
        rendered = shell_join(command)
        self.assertIn("docker run", rendered)
        self.assertIn("python:3.12-slim", rendered)
        self.assertIn("/workspace", rendered)
        self.assertIn("--network none", rendered)


if __name__ == "__main__":
    unittest.main()
