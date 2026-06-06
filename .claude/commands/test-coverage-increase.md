---
name: test-coverage-increase
description: Workflow command scaffold for test-coverage-increase in Star-Wars-Galactic-Battlegrounds-Save-Game-Editor.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /test-coverage-increase

Use this workflow when working on **test-coverage-increase** in `Star-Wars-Galactic-Battlegrounds-Save-Game-Editor`.

## Goal

Adds or updates tests to increase code coverage, often targeting specific branches or edge cases.

## Common Files

- `tests/test_swgb_save.py`
- `tests/test_swgb_save_gui.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify uncovered branches or lines in the codebase.
- Write new tests or update existing ones to cover these cases.
- Verify coverage locally (e.g., with pytest --cov).
- Commit test changes.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.
