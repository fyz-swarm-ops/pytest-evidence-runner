# Verification Report

**Verdict:** failed

**Summary:** Pytest completed in Docker with 1 failed and 0 errored tests.

## Run

- Run id: `run-7165a5526699`
- Execution mode: `docker`
- Exit code: `1`
- Duration: `1.305` seconds
- Tests: `4` total, `3` passed, `1` failed, `0` errors

## Test Cases

- `test-64dc442821f9f724` `passed` `tests.test_calculator.test_adds_numbers` (0.001s)
- `test-7fcf9195b9e086af` `failed` `tests.test_calculator.test_divides_numbers` (0.001s)
- `test-3c2ad2c09a2a32d1` `passed` `tests.test_calculator.test_normalizes_email` (0.0s)
- `test-0a9e36bce22309e3` `passed` `tests.test_calculator.test_multiplies_numbers` (0.0s)

## Failures

### `failure-0001` `failure`

Message: assert 2.6666666666666665 == 4
 +  where 2.6666666666666665 = divide(8, 2)

```text
def test_divides_numbers():
>       assert divide(8, 2) == 4
E       assert 2.6666666666666665 == 4
E        +  where 2.6666666666666665 = divide(8, 2)

tests/test_calculator.py:9: AssertionError
```

## Artifacts

- `raw/docker-command.json` `5471ff0f50a8cc5ed56b22929a7fabfbfe5c15a2dfbd9222cf330f582624edd2` (824 bytes)
- `raw/docker-config/config.json` `81bcbd3f950f2b31b87a64e8eca0de39db52feb0060d2bc631d7d794696604eb` (13 bytes)
- `raw/docker-run.stderr.log` `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes)
- `raw/docker-run.stdout.log` `f27fedba601dfca1f20015eccdf08792017006b7c5d5f2dd7ed8501ac6ee78b5` (1625 bytes)
- `raw/pytest-junit.xml` `6a2461532ed22f0cea7bec13707f1a1da58d40c7813420b595f7bac62da750b2` (912 bytes)

## Reproduce

- `python -m pytest_evidence_runner run --docker --project /workspace/pytest-evidence-runner/samples/regression_v2 --output-dir /workspace/pytest-evidence-runner/evidence/regression-v2-live`
- `docker run --name pytest-evidence-run-7165a5526699 --rm --network none --cpus 1 --memory 512m --pids-limit 256 --tmpfs /tmp:rw,nosuid,nodev,size=128m -v /workspace/pytest-evidence-runner/samples/regression_v2:/workspace:ro -v /workspace/pytest-evidence-runner/evidence/regression-v2-live:/evidence:rw -w /workspace --entrypoint python pytest-evidence-runner:local -m pytest -q --junitxml=/evidence/raw/pytest-junit.xml`
