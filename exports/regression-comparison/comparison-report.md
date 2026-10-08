# Evidence Comparison Report

**Verdict:** regression

**Summary:** The current run introduced regressions.

## Runs

- Baseline: `run-25f5aad19194` `passed` from `evidence/regression-v1-live/report.json`
- Current: `run-7165a5526699` `failed` from `evidence/regression-v2-live/report.json`

## Transition Counts

- Regressions: `1`
- Fixed: `0`
- Persistent failures: `0`
- Unchanged passing: `2`
- Added: `1`
- Removed: `0`
- Other changes: `0`

## Performance Counts

- Slower: `0`
- Faster: `1`
- Unchanged: `2`
- Not comparable: `1`

## Individual Test Transitions

| Test id | Test | Baseline | Current | Classification | Duration delta |
| --- | --- | --- | --- | --- | --- |
| `test-0a9e36bce22309e3` | tests.test_calculator.test_multiplies_numbers | missing | passed | added | n/a |
| `test-3c2ad2c09a2a32d1` | tests.test_calculator.test_normalizes_email | passed | passed | unchanged_passing | -0.001000s (faster) |
| `test-64dc442821f9f724` | tests.test_calculator.test_adds_numbers | passed | passed | unchanged_passing | +0.000000s (unchanged) |
| `test-7fcf9195b9e086af` | tests.test_calculator.test_divides_numbers | passed | failed | regression | +0.000000s (unchanged) |

## Evidence Links

### `test-0a9e36bce22309e3` tests.test_calculator.test_multiplies_numbers

- Classification: `added`
- Baseline source: `null`
- Current source: `{"failure_ids": [], "session_id": "session-pytest", "stderr_present": false, "stdout_present": false, "test_case_id": "test-0a9e36bce22309e3"}`
- Performance: `{"baseline_seconds": null, "classification": "not_comparable", "current_seconds": null}`

### `test-3c2ad2c09a2a32d1` tests.test_calculator.test_normalizes_email

- Classification: `unchanged_passing`
- Baseline source: `{"failure_ids": [], "session_id": "session-pytest", "stderr_present": false, "stdout_present": false, "test_case_id": "test-3c2ad2c09a2a32d1"}`
- Current source: `{"failure_ids": [], "session_id": "session-pytest", "stderr_present": false, "stdout_present": false, "test_case_id": "test-3c2ad2c09a2a32d1"}`
- Performance: `{"baseline_seconds": 0.001, "classification": "faster", "current_seconds": 0.0, "delta_percent": -100.0, "delta_seconds": -0.001}`

### `test-64dc442821f9f724` tests.test_calculator.test_adds_numbers

- Classification: `unchanged_passing`
- Baseline source: `{"failure_ids": [], "session_id": "session-pytest", "stderr_present": false, "stdout_present": false, "test_case_id": "test-64dc442821f9f724"}`
- Current source: `{"failure_ids": [], "session_id": "session-pytest", "stderr_present": false, "stdout_present": false, "test_case_id": "test-64dc442821f9f724"}`
- Performance: `{"baseline_seconds": 0.001, "classification": "unchanged", "current_seconds": 0.001, "delta_percent": 0.0, "delta_seconds": 0.0}`

### `test-7fcf9195b9e086af` tests.test_calculator.test_divides_numbers

- Classification: `regression`
- Baseline source: `{"failure_ids": [], "session_id": "session-pytest", "stderr_present": false, "stdout_present": false, "test_case_id": "test-7fcf9195b9e086af"}`
- Current source: `{"failure_ids": ["failure-0001"], "session_id": "session-pytest", "stderr_present": false, "stdout_present": false, "test_case_id": "test-7fcf9195b9e086af"}`
- Performance: `{"baseline_seconds": 0.001, "classification": "unchanged", "current_seconds": 0.001, "delta_percent": 0.0, "delta_seconds": 0.0}`
