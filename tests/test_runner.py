import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pytest_evidence_runner.docker import build_docker_command, shell_join
from pytest_evidence_runner.reporting import render_markdown, write_reports
from pytest_evidence_runner.runner import run_verification
from pytest_evidence_runner.text import timeout_output


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

    def test_timeout_preserves_partial_stdout_and_stderr(self):
        timeout = subprocess.TimeoutExpired(["python3"], timeout=1, output=b"partial stdout", stderr=b"partial stderr")
        with mock.patch("pytest_evidence_runner.runner.subprocess.run", side_effect=timeout):
            report = run_verification(["python3", "-c", "print('slow')"], SAMPLE, timeout_seconds=1)
        self.assertEqual(report.exit_code, 124)
        self.assertEqual(report.failure_kind, "timeout")
        self.assertIn("partial stdout", report.stdout)
        self.assertIn("partial stderr", report.stderr)
        self.assertIn("Command timed out after 1 seconds.", report.stderr)

    def test_voluntary_exit_124_is_not_classified_as_timeout(self):
        report = run_verification(["python3", "-c", "raise SystemExit(124)"], SAMPLE, timeout_seconds=30)
        self.assertEqual(report.exit_code, 124)
        self.assertEqual(report.failure_kind, "runner_error")
        self.assertIn("Command failed with exit code 124.", report.summary)

    def test_timeout_output_decodes_bytes_with_replacement(self):
        self.assertEqual(timeout_output(b"hello"), "hello")
        self.assertIn("\ufffd", timeout_output(b"\xff"))

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
