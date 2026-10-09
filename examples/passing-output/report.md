# Verification Report

**Verdict:** passed

**Summary:** Pytest completed successfully in Docker.

**Failure kind:** none

## Run

- Run id: `run-5df1fc44dd86`
- Execution mode: `docker`
- Started: `2026-10-08T17:29:21.356842+00:00`
- Finished: `2026-10-08T17:29:24.732899+00:00`
- Duration: `3.376` seconds
- Working directory: `/workspace/pytest-evidence-runner/samples/pytest_project`
- Command: `python -m pytest -q tests/test_calculator.py::test_add_passes tests/test_calculator.py::test_divide_passes`
- Exit code: `0`

## Container

- Container id/name: `pytest-evidence-run-5df1fc44dd86`
- Image: `pytest-evidence-runner:local`
- Image id: `sha256:eef206ef77923cb49c991246881e5d1e89b12533cf35daa7da7752273ec14c12`
- Docker: `Docker version 27.4.0, build bde2b89`
- Network disabled: `True`
- Privileged: `False`
- Resources: `cpus=1, memory=512m, pids_limit=256, tmpfs=/tmp:rw,nosuid,nodev,size=128m`
- Project mount: `/workspace/pytest-evidence-runner/samples/pytest_project:/workspace:ro`
- Evidence mount: `/workspace/pytest-evidence-runner/evidence/docker-passing-subset:/evidence:rw`

## Test Session

- Status: `passed`
- Total: `2`
- Passed: `2`
- Failed: `0`
- Errors: `0`
- Skipped: `0`

### Test Cases

- `test-0001` `passed` `tests.test_calculator.test_add_passes` (0.001s)
- `test-0002` `passed` `tests.test_calculator.test_divide_passes` (0.0s)

## Failures

- No structured failures captured.

## Evidence Hashes

- `app/__init__.py` `5eb3945eef525473781ad9407fd015705d874746c0eb3d3b9f0acfc7d9e18ea9` (65 bytes)
- `app/calculator.py` `8c573fde83318f6d8f81cd4243df1723cc9aae22c5caf827b40cd226eea91a81` (133 bytes)
- `tests/test_calculator.py` `d7e588c30e182220cd27f2258326ece66d7f4e8d8422192357b1511d133e9f9f` (210 bytes)

## Artifacts

- `raw/docker-build.stderr.log` `5743a10e5df1ddec74ff37f96def7ea76fd92f75ebeb1e068d8647bdca161dd3` (995 bytes)
- `raw/docker-build.stdout.log` `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes)
- `raw/docker-command.json` `eb93fc32f012f985f502e23efc8cfa9a5d792d52ec8a8559b127aca34d368286` (930 bytes)
- `raw/docker-run.stderr.log` `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes)
- `raw/docker-run.stdout.log` `fa2123cf13741ec93a1a52a47333f57f7483109af68bd292a2ba35b91ee1297a` (719 bytes)
- `raw/pytest-junit.xml` `83a12024c81ea19b726413cc258aefbc2dd83628cc10954589294777b3668d4b` (415 bytes)

## Stdout

```text
..                                                                       [100%]
=============================== warnings summary ===============================
../usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:475
  /usr/local/lib/python3.12/site-packages/_pytest/cacheprovider.py:475: PytestCacheWarning: could not create cache path /workspace/.pytest_cache/v/cache/nodeids: [Errno 30] Read-only file system: '/workspace/pytest-cache-files-pc0bzxqb'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
-------------- generated xml file: /evidence/raw/pytest-junit.xml --------------
2 passed, 1 warning in 0.04s
```

## Stderr

```text

```

## Reproduce

- `python -m pytest_evidence_runner run --docker --project /workspace/pytest-evidence-runner/samples/pytest_project --output-dir /workspace/pytest-evidence-runner/evidence/docker-passing-subset`
- `docker run --name pytest-evidence-run-5df1fc44dd86 --rm --network none --cpus 1 --memory 512m --pids-limit 256 --tmpfs /tmp:rw,nosuid,nodev,size=128m -v /workspace/pytest-evidence-runner/samples/pytest_project:/workspace:ro -v /workspace/pytest-evidence-runner/evidence/docker-passing-subset:/evidence:rw -w /workspace --entrypoint python pytest-evidence-runner:local -m pytest -q tests/test_calculator.py::test_add_passes tests/test_calculator.py::test_divide_passes --junitxml=/evidence/raw/pytest-junit.xml`
