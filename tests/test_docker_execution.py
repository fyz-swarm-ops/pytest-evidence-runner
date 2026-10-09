import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pytest_evidence_runner.docker import _docker_build_context, _parse_junit, run_pytest_in_docker
from pytest_evidence_runner.reporting import render_markdown, write_reports


SAMPLE = ROOT / "samples" / "pytest_project"


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    completed = subprocess.run(["docker", "info"], text=True, capture_output=True, check=False, timeout=15)
    return completed.returncode == 0


class DockerExecutionTests(unittest.TestCase):
    @unittest.skipUnless(docker_available(), "Docker daemon is not available")
    def test_actual_docker_execution_captures_failed_pytest_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_pytest_in_docker(SAMPLE, Path(tmp), timeout_seconds=180)
            self.assertEqual(report.execution_mode, "docker")
            self.assertEqual(report.verdict, "failed")
            self.assertEqual(report.failure_kind, "test_failure")
            self.assertIsNotNone(report.container)
            self.assertTrue(report.container.network_disabled)
            self.assertFalse(report.container.privileged)
            self.assertIsNotNone(report.test_session)
            self.assertEqual(report.test_session.total, 3)
            self.assertEqual(report.test_session.failed, 1)
            self.assertEqual(len(report.failures), 1)
            self.assertTrue((Path(tmp) / "raw" / "pytest-junit.xml").exists())
            json_path, md_path = write_reports(report, Path(tmp))
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            markdown = render_markdown(report)
            self.assertIn("test_intentional_failure_for_evidence", markdown)

    def test_missing_docker_daemon_is_reported_without_crashing(self):
        with mock.patch("pytest_evidence_runner.docker._docker_version", return_value=None):
            with tempfile.TemporaryDirectory() as tmp:
                report = run_pytest_in_docker(SAMPLE, Path(tmp), build_image=False)
        self.assertEqual(report.verdict, "error")
        self.assertEqual(report.failure_kind, "missing_docker")

    def test_default_dockerfile_is_packaged(self):
        with _docker_build_context() as context:
            self.assertTrue((context / "Dockerfile").exists())

    def test_docker_timeout_preserves_partial_stdout_and_stderr(self):
        timeout = subprocess.TimeoutExpired(["docker"], timeout=1, output=b"partial stdout", stderr=b"partial stderr")
        with mock.patch("pytest_evidence_runner.docker._docker_version", return_value="Docker version test"):
            with mock.patch("pytest_evidence_runner.docker._image_id", return_value="sha256:test"):
                with mock.patch("pytest_evidence_runner.docker._run") as fake_run:
                    fake_run.return_value = subprocess.CompletedProcess(["docker"], 0, "ok", "")
                    with mock.patch("pytest_evidence_runner.docker.subprocess.run", side_effect=timeout):
                        with tempfile.TemporaryDirectory() as tmp:
                            report = run_pytest_in_docker(SAMPLE, Path(tmp), timeout_seconds=1, build_image=False)
                            stdout_log = (Path(tmp) / "raw" / "docker-run.stdout.log").read_text(encoding="utf-8")
                            stderr_log = (Path(tmp) / "raw" / "docker-run.stderr.log").read_text(encoding="utf-8")
        self.assertEqual(report.failure_kind, "timeout")
        self.assertIn("partial stdout", report.stdout)
        self.assertIn("partial stderr", report.stderr)
        self.assertIn("Docker execution timed out after 1 seconds.", report.stderr)
        self.assertIn("partial stdout", stdout_log)
        self.assertIn("partial stderr", stderr_log)

    def test_malformed_junit_is_returned_as_structured_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pytest-junit.xml"
            path.write_text("<testsuite><testcase>", encoding="utf-8")
            started = finished = datetime.now(timezone.utc)
            session, cases, failures = _parse_junit(path, ["python", "-m", "pytest"], 1, started, finished)
        self.assertIsNotNone(session)
        self.assertEqual(session.status, "error")
        self.assertEqual(cases, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].kind, "junit_parse_error")


if __name__ == "__main__":
    unittest.main()
