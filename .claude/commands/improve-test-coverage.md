---
name: improve-test-coverage
description: Workflow command scaffold for improve-test-coverage in Star-Wars-Galactic-Battlegrounds-Save-Game-Editor.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /improve-test-coverage

Use this workflow when working on **improve-test-coverage** in `Star-Wars-Galactic-Battlegrounds-Save-Game-Editor`.

## Goal

Increase test coverage by adding tests for previously uncovered code branches.

## Common Files

- `tests/test_swgb_save.py`
- `tests/test_swgb_save_gui.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify uncovered code branches using coverage tools.
- Write new tests targeting those specific branches.
- Add or update test files accordingly.
- Verify that coverage reaches 100%.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.
