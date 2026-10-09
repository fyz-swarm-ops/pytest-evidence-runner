# Evidence Schema

`report.json` is the canonical machine-readable evidence file for one run. `report.md` is a human-readable rendering of the same run.

The schema is intentionally decomposable:

- `run_id` identifies one verification run.
- `container.id` identifies the Docker container attempt and records image, mounts, network/resource settings, and Docker version.
- `test_session.id` identifies the pytest session.
- `test_session.test_case_ids[]` links the session to `test_cases[]`.
- `test_cases[].failure_ids[]` links a test case to `failures[]`.
- `logs[]` preserves raw stdout/stderr with content hashes.
- `artifacts[]` records raw files such as `raw/pytest-junit.xml`, `raw/docker-run.stdout.log`, and `raw/docker-command.json`.
- `file_hashes[]` records selected project inputs for integrity and comparison across runs.
- `test_cases[].id` is a stable identifier derived from pytest `classname::name`, not execution order.

Important top-level fields:

- `verdict`: `passed`, `failed`, or `error`.
- `failure_kind`: `null`, `test_failure`, `timeout`, `missing_docker`, `docker_daemon_unavailable`, `docker_build_failed`, or `runner_error`.
- `execution_mode`: `local` or `docker`.
- `reproduction[]`: commands that reproduce the run.

The raw execution evidence should be preserved separately from summaries. Treat `report.json` and files under `raw/` as source evidence; regenerate summaries from them when needed.

## Comparison Schema

`comparison.json` is the canonical machine-readable comparison file produced by `pytest-evidence compare`.

Important top-level fields:

- `comparison_id` identifies one comparison operation.
- `baseline` and `current` link back to the source `report.json` files, run ids, verdicts, logs, and artifacts.
- `summary.counts` records regression, fixed, persistent failure, unchanged passing, added, removed, and other transition counts.
- `summary.performance_counts` records slower, faster, unchanged, and not-comparable duration changes.
- `transitions[]` contains one record per stable test id, with `baseline_source` and `current_source` references back to source test case ids and failure ids.
- `thresholds` records the duration thresholds used for performance classification.

Comparison reports do not rerun tests. They compare saved execution reports and preserve links back to the raw run evidence.

## Export Package Manifest

ZIP exports include `manifest.json` with SHA-256 hashes and execution metadata. These hashes provide package integrity checks for copied files; they are not a cryptographic signature and do not prove who created the package.

The test suite validates every checked-in evidence ZIP by comparing each
manifest entry's `sha256` and `size_bytes` against the actual ZIP member bytes.
