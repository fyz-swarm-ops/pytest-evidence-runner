# Verification Report

**Verdict:** failed

**Summary:** Pytest completed in Docker with 1 failed and 0 errored tests.

**Failure kind:** test_failure

## Run

- Run id: `run-4eeb9e7e021b`
- Execution mode: `docker`
- Started: `2026-10-08T17:28:30.958892+00:00`
- Finished: `2026-10-08T17:28:33.837818+00:00`
- Duration: `2.879` seconds
- Working directory: `/workspace/pytest-evidence-runner/samples/pytest_project`
- Command: `python -m pytest -q`
- Exit code: `1`

## Container

- Container id/name: `pytest-evidence-run-4eeb9e7e021b`
- Image: `pytest-evidence-runner:local`
- Image id: `sha256:eef206ef77923cb49c991246881e5d1e89b12533cf35daa7da7752273ec14c12`
- Docker: `Docker version 27.4.0, build bde2b89`
- Network disabled: `True`
- Privileged: `False`
- Resources: `cpus=1, memory=512m, pids_limit=256, tmpfs=/tmp:rw,nosuid,nodev,size=128m`
- Project mount: `/workspace/pytest-evidence-runner/samples/pytest_project:/workspace:ro`
- Evidence mount: `/workspace/pytest-evidence-runner/evidence/docker-sample:/evidence:rw`

## Test Session

- Status: `failed`
- Total: `3`
- Passed: `2`
- Failed: `1`
- Errors: `0`
- Skipped: `0`

### Test Cases

- `test-0001` `passed` `tests.test_calculator.test_add_passes` (0.001s)
- `test-0002` `passed` `tests.test_calculator.test_divide_passes` (0.0s)
- `test-0003` `failed` `tests.test_calculator.test_intentional_failure_for_evidence` (0.001s)

## Failures

### `failure-0001` `failure` in `tests.test_calculator.test_intentional_failure_for_evidence`

Message: assert 4 == 5
 +  where 4 = add(2, 2)

```text
def test_intentional_failure_for_evidence():
>       assert add(2, 2) == 5
E       assert 4 == 5
E        +  where 4 = add(2, 2)

tests/test_calculator.py:13: AssertionError
```

## Evidence Hashes

- `app/__init__.py` `5eb3945eef525473781ad9407fd015705d874746c0eb3d3b9f0acfc7d9e18ea9` (65 bytes)
- `app/calculator.py` `8c573fde83318f6d8f81cd4243df1723cc9aae22c5caf827b40cd226eea91a81` (133 bytes)
- `tests/test_calculator.py` `d7e588c30e182220cd27f2258326ece66d7f4e8d8422192357b1511d133e9f9f` (210 bytes)

## Artifacts

- `raw/docker-build.stderr.log` `408d42c52a5b6c2f9e159f0f2b6d001d744850d4a8907e5d523f6a1bca7f4192` (995 bytes)
- `raw/docker-build.stdout.log` `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes)
- `raw/docker-command.json` `8a832565c7b358c5bbb22d668f1fd3b8c827b612ff5ec3336cddc18c25ad0cb0` (825 bytes)
- `raw/docker-run.stderr.log` `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes)
- `raw/docker-run.stdout.log` `3d76cc868c7f5cd6cc5c8fd279d35145e5f40f7f88c49efc024c27ea65bf020b` (1603 bytes)
- `raw/pytest-junit.xml` `2f6fa2752e34b8da6edaca4fc7a47e87db6569830bac55f8243ce31be5130d5e` (775 bytes)

## Stdout

```text
..F                                                                      [100%]
=================================== FAILURES ===================================
____________________ test_intentional_failure_for_evidence _____________________

    def test_intentional_failure_for_evidence():
>       assert add(2, 2) == 5
E       assert 4 == 5
E        +  where 4 = add(2, 2)

tests/test_calculator.py:13: AssertionError
=============================== warnings summary ===============================
../usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:475
  /usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:475: PytestCacheWarning: could not create cache path /workspace/.pytest_cache/v/cache/nodeids: [Errno 30] Read-only file system: '/workspace/pytest-cache-files-lau76awe'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

../usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:429
  /usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:429: PytestCacheWarning: could not create cache path /workspace/.pytest_cache/v/cache/lastfailed: [Errno 30] Read-only file system: '/workspace/pytest-cache-files-zocvccjf'
    config.cache.set("cache/lastfailed", self.lastfailed)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
-------------- generated xml file: /evidence/raw/pytest-junit.xml --------------
=========================== short test summary info ============================
FAILED tests/test_calculator.py::test_intentional_failure_for_evidence - asse...
1 failed, 2 passed, 2 warnings in 0.08s
```

## Stderr

```text

```

## Reproduce

- `python -m pytest_evidence_runner run --docker --project /workspace/pytest-evidence-runner/samples/pytest_project --output-dir /workspace/pytest-evidence-runner/evidence/docker-sample`
- `docker run --name pytest-evidence-run-4eeb9e7e021b --rm --network none --cpus 1 --memory 512m --pids-limit 256 --tmpfs /tmp:rw,nosuid,nodev,size=128m -v /workspace/pytest-evidence-runner/samples/pytest_project:/workspace:ro -v /workspace/pytest-evidence-runner/evidence/docker-sample:/evidence:rw -w /workspace --entrypoint python pytest-evidence-runner:local -m pytest -q --junitxml=/evidence/raw/pytest-junit.xml`
