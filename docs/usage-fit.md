# Usage Fit

Pytest Evidence Runner is a small verification utility. It is a good fit when a
test result needs portable evidence, not just a pass/fail summary.

## Good Fit

- Bounded pytest failure reproduction.
- Independent verification of small test-suite findings.
- Baseline-to-current regression comparison.
- Evidence packets for code review, QA handoff, or bug reproduction.

## Poor Fit

- Full security audits.
- Production incident response without separate access boundaries.
- Large migrations or refactors disguised as a quick verification task.
- Untrusted code execution without Docker or another machine/account boundary.

## Expected Output

The tool standardizes command capture, environment metadata, evidence hashes,
report formats, and handoff summaries. The generated reports should still be
read as evidence for one bounded run, not as a broad certification of a project.
