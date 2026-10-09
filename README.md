# Pytest Evidence Runner

Pytest Evidence Runner runs Python test commands and writes evidence reports that
can be inspected, compared, exported, and shared. It is meant for bounded QA,
code-review, and bug-reproduction work where the useful output is not only
"tests failed," but what ran, where it ran, what failed, and how to reproduce it.

## Features

- Run pytest in a constrained Docker container with no network access.
- Run local commands when Docker isolation is not needed.
- Capture stdout, stderr, exit code, duration, Docker metadata, JUnit XML,
  selected file hashes, raw logs, and reproduction commands.
- Write `report.json` and `report.md` for each run.
- Save baselines and compare reports without rerunning tests.
- Export standalone HTML, PDF, JSON, Markdown, and ZIP evidence packages.

## Install

From a checkout:

```bash
python3 -m pip install -e .
```

From a built wheel:

```bash
python3 -m pip install dist/pytest_evidence_runner-0.1.1-py3-none-any.whl
```

Docker execution requires Docker to be installed and the daemon to be running.

## Run A Sample

The sample project contains two passing tests and one intentional failing test:

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project samples/pytest_project \
  --output-dir evidence/docker-sample
```

Expected result: the command exits non-zero because the sample includes an
intentional assertion failure. The report still writes successfully:

```text
wrote evidence/docker-sample/report.json
wrote evidence/docker-sample/report.md
```

Inspect the result:

```bash
python3 -m json.tool evidence/docker-sample/report.json | sed -n '1,80p'
sed -n '1,120p' evidence/docker-sample/raw/docker-run.stdout.log
```

Run a local command instead:

```bash
python3 -m pytest_evidence_runner run \
  --workdir samples/unittest_project \
  --output-dir evidence/local-unittest \
  -- python3 -m unittest discover -s tests
```

## Compare Regressions

The repository includes two Docker-runnable sample versions:

- `samples/regression_v1`: all tests pass.
- `samples/regression_v2`: one test intentionally regresses and one new test is added.

Run both versions:

```bash
python3 -m pytest_evidence_runner run \
  --docker \
  --project samples/regression_v1 \
  --output-dir evidence/regression-v1

python3 -m pytest_evidence_runner run \
  --docker \
  --project samples/regression_v2 \
  --output-dir evidence/regression-v2
```

Compare the saved reports:

```bash
python3 -m pytest_evidence_runner compare \
  --baseline evidence/regression-v1/report.json \
  --current evidence/regression-v2/report.json \
  --output-dir evidence/regression-comparison
```

The comparison report classifies stable test-id transitions:

- `regression`: passed to failed/error
- `fixed`: failed/error to passed
- `persistent_failure`: failed/error to failed/error
- `unchanged_passing`: passed to passed
- `added`: current run only
- `removed`: baseline run only

## Export Reports

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

Generated files are portable:

- `run-report.html` / `comparison-report.html`: browser-readable reports.
- `run-report.pdf` / `comparison-report.pdf`: compact summaries.
- `*.json`: machine-readable evidence.
- `*.md`: GitHub/PR-friendly reports.
- `*-evidence-package.zip`: reports plus raw evidence and `manifest.json` hashes.

## Report Contents

`report.json` is the canonical machine-readable file. Important fields include:

- run id, timestamps, duration, command, exit code, verdict, and failure kind;
- Docker/container metadata for Docker runs;
- pytest session totals, test cases, linked failures, and raw logs;
- selected source/config file hashes;
- raw artifacts such as JUnit XML and Docker stdout/stderr logs;
- reproduction commands.

See `docs/evidence-schema.md` for schema relationships.

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

The tool still executes test code from the target project. Do not run untrusted
projects without an appropriate machine or account boundary.

## Limitations

- Docker mode depends on a working local Docker daemon.
- The default Docker image is built locally from a small packaged build context.
- The runner captures command output and pytest/JUnit evidence; it is not a
  security sandbox or a full test-orchestration platform.
- PDF export is intentionally simple and dependency-free. Use HTML/JSON/Markdown
  for detailed drilldown.
- ZIP manifest hashes provide file integrity checks, not author signatures.

## Troubleshooting

- `missing_docker`: Docker CLI is not installed or not on `PATH`.
- `docker_daemon_unavailable`: Docker is installed but the daemon is not reachable.
- `docker_build_failed`: the local test image could not be built.
- `timeout`: the command exceeded `--timeout-seconds`.
- `runner_error`: pytest did not produce structured test results.
- `test_failure`: pytest ran and reported failing/erroring tests.

If Docker Desktop reports a credential-helper or base-image metadata error while
building the local image, verify Docker can pull the base image directly:

```bash
docker pull python:3.12-slim
```
