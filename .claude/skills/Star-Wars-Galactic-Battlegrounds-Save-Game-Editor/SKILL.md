```markdown
# Star-Wars-Galactic-Battlegrounds-Save-Game-Editor Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the development patterns, coding conventions, and common workflows used in the **Star-Wars-Galactic-Battlegrounds-Save-Game-Editor** Python project. The repository is a save game editor for the classic Star Wars: Galactic Battlegrounds game, featuring a Python codebase with both CLI and GUI components. The project emphasizes code style consistency, test coverage, and Python best practices, with well-defined workflows for maintaining code quality.

---

## Coding Conventions

### File Naming

- **Snake case** is used for all Python files.
  - Example: `swgb_save.py`, `swgb_save_gui.py`, `test_swgb_save.py`

### Import Style

- **Relative imports** are preferred within the package.
  - Example:
    ```python
    from .swgb_save import SaveGame
    ```

### Export Style

- **Named exports** are used; modules explicitly define what is exported.
  - Example:
    ```python
    __all__ = ["SaveGame", "SaveGameEditor"]
    ```

### Commit Messages

- **Conventional commit** prefixes are used, such as `style:` and `test:`.
  - Example:  
    ```
    style: apply Black formatting to swgb_save.py and tests
    test: add edge case tests for invalid save file headers
    ```

---

## Workflows

### Code Style and Linting Corrections

**Trigger:** When you want to enforce consistent code style or resolve linter/formatter warnings.  
**Command:** `/format-code`

1. Run code formatters (e.g., `autopep8`, `black`, `isort`) on all code and test files.
2. Apply any necessary manual fixes to resolve linter warnings.
3. Commit changes to both source and test files.

**Files involved:**  
- `swgb_save.py`  
- `swgb_save_gui.py`  
- `tests/test_swgb_save.py`  
- `tests/test_swgb_save_gui.py`

**Example:**
```bash
black swgb_save.py swgb_save_gui.py tests/
isort swgb_save.py swgb_save_gui.py tests/
# Manually fix any remaining linter warnings
git commit -am "style: apply code formatting and lint fixes"
```

---

### Test Coverage Increase

**Trigger:** When you want to achieve or maintain 100% test coverage, especially for branches and edge cases.  
**Command:** `/increase-coverage`

1. Identify uncovered branches or lines (e.g., using `pytest --cov`).
2. Write new tests or update existing ones to cover these cases.
3. Verify coverage locally.
4. Commit test changes.

**Files involved:**  
- `tests/test_swgb_save.py`  
- `tests/test_swgb_save_gui.py`

**Example:**
```bash
pytest --cov=.
# Add tests for uncovered code paths
git add tests/
git commit -m "test: increase coverage for SaveGame edge cases"
```

---

### Python Compatibility and Best Practice Fixes

**Trigger:** When you want to resolve compatibility or best-practice warnings (e.g., from Codacy or Pylint).  
**Command:** `/fix-python-compat`

1. Add necessary `__future__` imports for compatibility.
2. Refactor methods (e.g., convert to `@staticmethod`) as per linter suggestions.
3. Commit changes to affected source files.

**Files involved:**  
- `swgb_save.py`  
- `swgb_save_gui.py`

**Example:**
```python
from __future__ import annotations

class SaveGame:
    @staticmethod
    def parse_header(data: bytes) -> dict:
        ...
```
```bash
git commit -am "style: add __future__ imports and refactor to staticmethods"
```

---

## Testing Patterns

- **Test files** are named using the pattern `test_*.py` and placed in a `tests/` directory.
- Test functions are written using standard Python `assert` statements.
- The testing framework is not explicitly specified, but `pytest` conventions are compatible.

**Example:**
```python
def test_parse_header_valid():
    data = b"SWGB"
    result = parse_header(data)
    assert result["magic"] == "SWGB"
```

---

## Commands

| Command             | Purpose                                                      |
|---------------------|--------------------------------------------------------------|
| /format-code        | Standardize code formatting and resolve linter warnings      |
| /increase-coverage  | Add or update tests to increase code coverage                |
| /fix-python-compat  | Apply Python compatibility imports and best-practice fixes   |
```
