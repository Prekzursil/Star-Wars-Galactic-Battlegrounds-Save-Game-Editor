---
name: code-style-and-linting-corrections
description: Workflow command scaffold for code-style-and-linting-corrections in Star-Wars-Galactic-Battlegrounds-Save-Game-Editor.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /code-style-and-linting-corrections

Use this workflow when working on **code-style-and-linting-corrections** in `Star-Wars-Galactic-Battlegrounds-Save-Game-Editor`.

## Goal

Standardizes code formatting and resolves style/linting warnings across source and test files.

## Common Files

- `swgb_save.py`
- `swgb_save_gui.py`
- `tests/test_swgb_save.py`
- `tests/test_swgb_save_gui.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Run code formatters (e.g., Autopep8, Black, isort, etc.) on all code and test files.
- Apply any necessary manual fixes to resolve linter warnings.
- Commit changes to both source and test files.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.