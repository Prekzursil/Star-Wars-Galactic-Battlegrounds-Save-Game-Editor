---
name: address-code-style-and-lint-findings
description: Workflow command scaffold for address-code-style-and-lint-findings in Star-Wars-Galactic-Battlegrounds-Save-Game-Editor.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /address-code-style-and-lint-findings

Use this workflow when working on **address-code-style-and-lint-findings** in `Star-Wars-Galactic-Battlegrounds-Save-Game-Editor`.

## Goal

Resolve code style, compatibility, or linter warnings by updating code to follow best practices.

## Common Files

- `swgb_save.py`
- `swgb_save_gui.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify style or compatibility warnings from linter/static analysis.
- Update code to resolve the warnings (e.g., add **future** imports, refactor methods).
- Ensure behavior is preserved and all tests pass.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.
