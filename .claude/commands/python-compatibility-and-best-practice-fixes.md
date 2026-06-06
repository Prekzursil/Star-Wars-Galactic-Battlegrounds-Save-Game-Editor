---
name: python-compatibility-and-best-practice-fixes
description: Workflow command scaffold for python-compatibility-and-best-practice-fixes in Star-Wars-Galactic-Battlegrounds-Save-Game-Editor.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /python-compatibility-and-best-practice-fixes

Use this workflow when working on **python-compatibility-and-best-practice-fixes** in `Star-Wars-Galactic-Battlegrounds-Save-Game-Editor`.

## Goal

Applies Python compatibility imports and best-practice refactoring (e.g., staticmethod conversion) to source files.

## Common Files

- `swgb_save.py`
- `swgb_save_gui.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Add necessary __future__ imports for compatibility.
- Refactor methods (e.g., to staticmethod) as per linter suggestions.
- Commit changes to affected source files.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.