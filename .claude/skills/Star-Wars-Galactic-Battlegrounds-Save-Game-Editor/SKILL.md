```markdown
# Star-Wars-Galactic-Battlegrounds-Save-Game-Editor Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill outlines the development practices and workflows used in the **Star-Wars-Galactic-Battlegrounds-Save-Game-Editor** Python project. The repository focuses on editing save game files for the classic Star Wars: Galactic Battlegrounds game. It emphasizes maintainable code, clear commit conventions, and robust testing, even without a formal framework.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files and modules.
  ```
  # Good
  swgb_save.py
  test_swgb_save.py

  # Bad
  SWGBSave.py
  swgbSave.py
  ```

- **Import Style:**  
  Prefer **relative imports** within the package.
  ```python
  # Good
  from .swgb_save import SaveGameEditor

  # Bad
  import swgb_save
  ```

- **Export Style:**  
  Use **named exports** (explicitly define what is exported).
  ```python
  # In swgb_save.py
  __all__ = ['SaveGameEditor', 'parse_save_file']
  ```

- **Commit Messages:**  
  Follow the **conventional commit** format with prefixes such as `test` and `style`.
  ```
  test: add edge case tests for save file parsing
  style: refactor variable names for clarity
  ```

## Workflows

### Improve Test Coverage
**Trigger:** When you want to achieve 100% test coverage or cover missing code branches.  
**Command:** `/add-coverage-tests`

1. Identify uncovered code branches using a coverage tool (e.g., `coverage.py`).
2. Write new tests targeting those specific branches.
3. Add or update test files, such as `tests/test_swgb_save.py` or `tests/test_swgb_save_gui.py`.
4. Run the tests and verify that coverage reaches 100%.

**Example:**
```bash
coverage run -m unittest discover
coverage report
# Add tests for uncovered lines/functions
```

### Address Code Style and Lint Findings
**Trigger:** When you want to resolve linter or static analysis warnings (e.g., from Pylint or Codacy).  
**Command:** `/fix-lint-warnings`

1. Run a linter or static analysis tool to identify style or compatibility warnings.
   ```bash
   pylint swgb_save.py swgb_save_gui.py
   ```
2. Update the code to resolve the warnings (e.g., add `__future__` imports, refactor methods, fix naming).
3. Ensure all tests pass after making changes.

**Example:**
```python
# Add at the top of Python 2/3 compatible files
from __future__ import print_function

# Refactor long functions into smaller ones, fix variable names, etc.
```

## Testing Patterns

- **Test Files:**  
  Test files are named using the pattern `*.test.*` (e.g., `test_swgb_save.py`).
- **Test Framework:**  
  No specific test framework is enforced; use standard Python `unittest` or similar.
- **Test Structure:**  
  Place test files under a `tests/` directory.  
  Each test targets a specific module or GUI component.

**Example:**
```python
# tests/test_swgb_save.py
import unittest
from ..swgb_save import SaveGameEditor

class TestSaveGameEditor(unittest.TestCase):
    def test_parse_valid_file(self):
        editor = SaveGameEditor('test.sav')
        self.assertTrue(editor.is_valid())
```

## Commands

| Command                | Purpose                                                    |
|------------------------|------------------------------------------------------------|
| /add-coverage-tests    | Add tests to increase code coverage and cover missing branches |
| /fix-lint-warnings     | Resolve linter or static analysis warnings                  |
```
