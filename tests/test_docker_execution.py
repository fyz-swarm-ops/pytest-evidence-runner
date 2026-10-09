import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from pytest_evidence_runner.docker import _docker_build_context, _parse_junit, _run, run_pytest_in_docker
from pytest_evidence_runner.reporting import render_markdown, write_reports

ROOT = Path(__file__).resolve().parents[1]
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
            if report.failure_kind == "docker_build_failed" and "activity" in report.stderr.lower():
                self.skipTest(f"Docker image build is unavailable in this environment: {report.stderr[:200]}")
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

    def test_raw_cleanup_failure_is_reported_on_early_infrastructure_failure(self):
        with mock.patch("pytest_evidence_runner.docker._reset_raw_dir", return_value="stale.log: permission denied"):
            with mock.patch("pytest_evidence_runner.docker._docker_version", return_value=None):
                with tempfile.TemporaryDirectory() as tmp:
                    report = run_pytest_in_docker(SAMPLE, Path(tmp), build_image=False)
        self.assertEqual(report.failure_kind, "missing_docker")
        self.assertTrue(any(failure.kind == "raw_cleanup_failed" for failure in report.failures))
        self.assertIn("permission denied", report.failures[0].details)

    def test_docker_execution_preserves_existing_docker_configuration(self):
        seen_envs = []

        def fake_run(command, *args, **kwargs):
            seen_envs.append(kwargs.get("env") or {})
            if command[:3] == ["docker", "image", "inspect"]:
                return subprocess.CompletedProcess(command, 0, "sha256:test\n", "")
            return subprocess.CompletedProcess(command, 0, "{}", "")

        completed = subprocess.CompletedProcess(["docker"], 0, "ok", "")
        with mock.patch.dict("os.environ", {"DOCKER_CONFIG": "/operator/docker-config"}, clear=True):
            with mock.patch("pytest_evidence_runner.docker._docker_version", return_value="Docker version test"):
                with mock.patch("pytest_evidence_runner.docker._run", side_effect=fake_run):
                    with mock.patch("pytest_evidence_runner.docker.subprocess.run", return_value=completed):
                        with tempfile.TemporaryDirectory() as tmp:
                            run_pytest_in_docker(SAMPLE, Path(tmp), timeout_seconds=1, build_image=False)
        self.assertTrue(seen_envs)
        self.assertTrue(all(env.get("DOCKER_CONFIG") == "/operator/docker-config" for env in seen_envs))

    def test_docker_execution_does_not_create_config_inside_evidence(self):
        completed = subprocess.CompletedProcess(["docker"], 0, "ok", "")
        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("pytest_evidence_runner.docker._docker_version", return_value="Docker version test"):
                with mock.patch("pytest_evidence_runner.docker._run") as fake_run:
                    fake_run.return_value = subprocess.CompletedProcess(["docker"], 0, "{}", "")
                    with mock.patch("pytest_evidence_runner.docker.subprocess.run", return_value=completed):
                        with tempfile.TemporaryDirectory() as tmp:
                            raw_dir = Path(tmp) / "raw"
                            run_pytest_in_docker(SAMPLE, Path(tmp), timeout_seconds=1, build_image=False)
        self.assertFalse((raw_dir / "docker-config").exists())

    def test_docker_info_exception_returns_structured_failure(self):
        with mock.patch("pytest_evidence_runner.docker._docker_version", return_value="Docker version test"):
            with mock.patch("pytest_evidence_runner.docker._run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess(["docker", "info"], 1, "", "docker info failed")
                with tempfile.TemporaryDirectory() as tmp:
                    report = run_pytest_in_docker(SAMPLE, Path(tmp), build_image=False)
        self.assertEqual(report.verdict, "error")
        self.assertEqual(report.failure_kind, "docker_daemon_unavailable")
        self.assertIn("docker info failed", report.summary)

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

    def test_cleanup_failure_does_not_prevent_report(self):
        def fake_run(command, *args, **kwargs):
            if command[:3] == ["docker", "rm", "-f"]:
                return subprocess.CompletedProcess(command, 1, "", "cleanup failed")
            if command[:3] == ["docker", "image", "inspect"]:
                return subprocess.CompletedProcess(command, 0, "sha256:test\n", "")
            return subprocess.CompletedProcess(command, 0, "{}", "")

        completed = subprocess.CompletedProcess(["docker"], 0, "ok", "")
        with mock.patch("pytest_evidence_runner.docker._docker_version", return_value="Docker version test"):
            with mock.patch("pytest_evidence_runner.docker._run", side_effect=fake_run):
                with mock.patch("pytest_evidence_runner.docker.subprocess.run", return_value=completed):
                    with tempfile.TemporaryDirectory() as tmp:
                        report = run_pytest_in_docker(SAMPLE, Path(tmp), timeout_seconds=1, build_image=False)
                        stdout_log = (Path(tmp) / "raw" / "docker-run.stdout.log").read_text(encoding="utf-8")
        self.assertEqual(report.stdout, "ok")
        self.assertEqual(stdout_log, "ok")
        self.assertEqual(report.verdict, "error")
        self.assertEqual(report.failure_kind, "runner_error")
        self.assertTrue(any(failure.kind == "docker_cleanup_failed" for failure in report.failures))

    def test_reused_output_dir_does_not_parse_stale_junit(self):
        stale_junit = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" errors="0" failures="1" skipped="0" tests="1" time="0.1">
  <testcase classname="tests.old" name="test_old_failure" time="0.1">
    <failure message="old failure">old details</failure>
  </testcase>
</testsuite>
"""

        def fake_run(command, *args, **kwargs):
            if command[:3] == ["docker", "image", "inspect"]:
                return subprocess.CompletedProcess(command, 0, "sha256:test\n", "")
            return subprocess.CompletedProcess(command, 0, "{}", "")

        completed = subprocess.CompletedProcess(["docker"], 2, "failed before junit", "")
        with mock.patch("pytest_evidence_runner.docker._docker_version", return_value="Docker version test"):
            with mock.patch("pytest_evidence_runner.docker._run", side_effect=fake_run):
                with mock.patch("pytest_evidence_runner.docker.subprocess.run", return_value=completed):
                    with tempfile.TemporaryDirectory() as tmp:
                        raw_dir = Path(tmp) / "raw"
                        raw_dir.mkdir()
                        (raw_dir / "pytest-junit.xml").write_text(stale_junit, encoding="utf-8")
                        report = run_pytest_in_docker(SAMPLE, Path(tmp), timeout_seconds=1, build_image=False)
        self.assertEqual(report.verdict, "error")
        self.assertEqual(report.failure_kind, "runner_error")
        self.assertIsNone(report.test_session)
        self.assertEqual(report.test_cases, [])
        self.assertFalse(any("test_old_failure" in failure.details for failure in report.failures))

    def test_run_converts_subprocess_timeout_to_completed_process(self):
        timeout = subprocess.TimeoutExpired(["docker", "info"], timeout=1, output=b"out", stderr=b"err")
        with mock.patch("pytest_evidence_runner.docker.subprocess.run", side_effect=timeout):
            completed = _run(["docker", "info"], timeout=1)
        self.assertEqual(completed.returncode, 124)
        self.assertIn("out", completed.stdout)
        self.assertIn("err", completed.stderr)

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
