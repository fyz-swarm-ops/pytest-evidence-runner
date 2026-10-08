# Pytest Evidence Runner

Pytest Evidence Runner runs Python tests in a bounded Docker container and produces evidence that an engineer can inspect, compare, and hand to a client. It is built for small QA, code-audit, and bug-reproduction engagements where the useful output is not just "tests failed," but what ran, where it ran, which tests failed, what logs were produced, and how to reproduce the result.

Publication status: public verified release. Docker execution, regression comparison, and report exports have been tested against a real local Docker daemon.

## What It Does

- validates Docker availability;
- builds a local test image when needed;
- mounts the target project read-only into `/workspace`;
- runs pytest inside the container with network disabled and resource limits;
- captures stdout, stderr, exit code, duration, Docker metadata, JUnit XML, logs, and file hashes;
- writes machine-readable `report.json` and human-readable `report.md`;
- saves named baselines and compares saved reports without rerunning tests;
- exports standalone HTML/PDF/JSON/Markdown reports and ZIP evidence packages;
- decomposes evidence into run, container, test session, test cases, failures, logs, artifacts, and reproduction steps.

## Install

From this directory:

```bash
python3 -m pip install -e .
```

Docker must be installed and the daemon must be running for `--docker` execution.

## Run The Sample In Docker

The sample project contains two passing tests and one intentional failing test:

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project samples/pytest_project \
  --output-dir evidence/docker-sample
```

Expected result: the command exits non-zero because the sample includes an intentional assertion failure. The report still writes successfully:

```text
wrote evidence/docker-sample/report.json
wrote evidence/docker-sample/report.md
```

This repository includes a real generated Docker failure report at `examples/verified-output/` and a real generated Docker passing-subset report at `examples/passing-output/`.

Inspect the overall result:

```bash
python3 -m json.tool evidence/docker-sample/report.json | sed -n '1,80p'
```

Drill into one failed test:

```bash
python3 - <<'PY'
import json
data = json.load(open("evidence/docker-sample/report.json"))
for failure in data["failures"]:
    print(failure["id"], failure["test_case_id"], failure["message"])
    print(failure["details"][:800])
PY
```

Examine raw logs and artifacts:

```bash
ls -R evidence/docker-sample/raw
sed -n '1,120p' evidence/docker-sample/raw/docker-run.stdout.log
```

Reproduce the failure:

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project samples/pytest_project \
  --output-dir evidence/reproduced-sample
```

Save a baseline and compare two runs:

```bash
python3 -m pytest_evidence_runner baseline save \
  --name sample-v1 \
  --report evidence/docker-sample/report.json

python3 -m pytest_evidence_runner compare \
  --baseline evidence/docker-sample/report.json \
  --current evidence/reproduced-sample/report.json \
  --output-dir evidence/sample-comparison
```

Inspect the included passing subset:

```bash
python3 -m json.tool examples/passing-output/report.json | sed -n '1,80p'
```

## Regression Comparison Workflow

The repository includes two Docker-runnable sample versions:

- `samples/regression_v1`: all tests pass.
- `samples/regression_v2`: one test intentionally regresses and one new test is added.

Run version A in Docker:

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project samples/regression_v1 \
  --output-dir evidence/regression-v1
```

Save the baseline:

```bash
python3 -m pytest_evidence_runner baseline save \
  --name regression-v1 \
  --report evidence/regression-v1/report.json
```

Run version B in Docker:

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project samples/regression_v2 \
  --output-dir evidence/regression-v2
```

Compare the results without rerunning tests:

```bash
python3 -m pytest_evidence_runner compare \
  --baseline evidence/regression-v1/report.json \
  --current evidence/regression-v2/report.json \
  --output-dir evidence/regression-comparison
```

Representative comparison output:

```text
wrote evidence/regression-comparison/comparison.json
wrote evidence/regression-comparison/comparison.md
```

The comparison report classifies stable test-id transitions:

- `regression`: passed -> failed/error
- `fixed`: failed/error -> passed
- `persistent_failure`: failed/error -> failed/error
- `unchanged_passing`: passed -> passed
- `added`: current run only
- `removed`: baseline only

Drill into the failing test evidence:

```bash
python3 - <<'PY'
import json
comparison = json.load(open("evidence/regression-comparison/comparison.json"))
for item in comparison["transitions"]:
    if item["classification"] == "regression":
        print(item["test_id"], item["name"])
        print(item["current_source"])
PY
```

Then inspect the raw current-run artifacts referenced by the comparison:

```bash
sed -n '1,160p' evidence/regression-v2/raw/docker-run.stdout.log
python3 -m json.tool evidence/regression-v2/report.json | sed -n '1,160p'
```

This repository includes real generated examples from that workflow:

- `examples/verified-output/report.json`
- `examples/verified-output/report.md`
- `examples/passing-output/report.json`
- `examples/passing-output/report.md`
- `exports/regression-v2/run-report.json`
- `exports/regression-v2/run-report.md`
- `exports/regression-v2/run-report.html`
- `exports/regression-v2/run-report.pdf`
- `exports/regression-v2/run-evidence-package.zip`
- `exports/regression-comparison/comparison-report.json`
- `exports/regression-comparison/comparison-report.md`
- `exports/regression-comparison/comparison-report.html`
- `exports/regression-comparison/comparison-report.pdf`
- `exports/regression-comparison/comparison-evidence-package.zip`

## Export Downloadable Reports

Export one run:

```bash
python3 -m pytest_evidence_runner export \
  --run evidence/regression-v2 \
  --format pdf,html,json,md,zip \
  --output exports/regression-v2
```

Export one comparison:

```bash
python3 -m pytest_evidence_runner export \
  --comparison evidence/regression-comparison \
  --format pdf,html,json,md,zip \
  --output exports/regression-comparison
```

Generated files are standalone and portable:

- `run-report.html` / `comparison-report.html`: expandable local browser reports.
- `run-report.pdf` / `comparison-report.pdf`: compact human-readable PDF summaries.
- `*.json`: complete machine-readable evidence or comparison data.
- `*.md`: readable GitHub/PR-friendly reports.
- `*-evidence-package.zip`: reports plus raw evidence and a `manifest.json` of file hashes.

Representative HTML preview:

```html
<details>
  <summary><code>test-...</code> regression</summary>
  <pre>{ "... linked source evidence ..." }</pre>
</details>
```

## Run Another Pytest Project

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project /path/to/project \
  --output-dir evidence/client-run \
  --timeout-seconds 180
```

The default Docker command is:

```bash
python -m pytest -q
```

Pass a custom pytest command after `--`:

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project /path/to/project \
  --output-dir evidence/client-run \
  -- python -m pytest tests/test_api.py -q
```

## Report Contents

`report.json` is the canonical machine-readable evidence file. `report.md` is a readable summary generated from the same data.

Important fields:

- `run_id`, timestamps, duration, command, exit code, verdict;
- `failure_kind`, distinguishing test failures from Docker/build/timeout/runner errors;
- `container`, including image, Docker version, mounts, no-network setting, privileged=false, and resource limits;
- `test_session`, with aggregate pytest counts;
- `test_cases[]`, each with stable ids and status;
- `failures[]`, linked back to test cases;
- `logs[]`, preserving raw stdout/stderr with hashes;
- `artifacts[]`, including JUnit XML and raw Docker logs;
- `file_hashes[]`, for selected source/config inputs;
- `reproduction[]`, with commands to rerun the evidence.

See `docs/evidence-schema.md` for the documented schema relationships.

## Safety Model

Docker execution uses conservative defaults:

- project mounted read-only at `/workspace`;
- evidence directory mounted read/write at `/evidence`;
- `--network none`;
- `--cpus 1`;
- `--memory 512m`;
- `--pids-limit 256`;
- no privileged container;
- no host networking;
- no Docker socket mounted into the test container.

The tool still executes test code from the target project. Do not run untrusted projects without accepting that risk and using an appropriate machine/account boundary.

## Troubleshooting

- `missing_docker`: Docker CLI is not installed or not on `PATH`.
- `docker_daemon_unavailable`: Docker is installed but the daemon is not reachable.
- `docker_build_failed`: the local test image could not be built.
- `timeout`: the container exceeded `--timeout-seconds`.
- `runner_error`: pytest did not produce structured test results.
- `test_failure`: pytest ran and reported failing/erroring tests.

If Docker Desktop reports a credential-helper or base-image metadata error while
building the local image, verify Docker can pull the base image directly:

```bash
docker pull python:3.12-slim
```

Then rerun the `pytest-evidence` command. This does not change the evidence
output; it only confirms Docker can resolve the public Python base image.

## Local Non-Docker Mode

For quick local command evidence:

```bash
python3 -m pytest_evidence_runner run \
  --workdir samples/unittest_project \
  --output-dir evidence/local-unittest \
  -- python3 -m unittest discover -s tests
```

Local mode is not a substitute for Docker isolation.
