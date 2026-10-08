import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pytest_evidence_runner.docker import DEFAULT_IMAGE, run_pytest_in_docker
from pytest_evidence_runner.reporting import render_markdown, write_reports


SAMPLE = ROOT / "samples" / "pytest_project"


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    completed = subprocess.run(["docker", "info"], text=True, capture_output=True, check=False, timeout=15)
    return completed.returncode == 0


def local_image_available() -> bool:
    if not docker_available():
        return False
    completed = subprocess.run(
        ["docker", "image", "inspect", DEFAULT_IMAGE],
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    return completed.returncode == 0


class DockerExecutionTests(unittest.TestCase):
    @unittest.skipUnless(local_image_available(), "Docker daemon or local pytest evidence image is not available")
    def test_actual_docker_execution_captures_failed_pytest_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_pytest_in_docker(SAMPLE, Path(tmp), timeout_seconds=180, build_image=False)
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


if __name__ == "__main__":
    unittest.main()
