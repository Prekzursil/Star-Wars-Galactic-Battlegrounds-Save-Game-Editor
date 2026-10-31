# Contributing to SWGB Save Editor

Thanks for wanting to help! This guide explains how changes get into
`Prekzursil/Star-Wars-Galactic-Battlegrounds-Save-Game-Editor` and the quality
bar every change has to clear.

Bugs and feature requests go through the
[issue tracker](https://github.com/Prekzursil/Star-Wars-Galactic-Battlegrounds-Save-Game-Editor/issues/new/choose).
Anything that looks security-sensitive does **not** — follow
[SECURITY.md](SECURITY.md) instead.

## The one rule

**Every gate must pass for the right reason. Never weaken a gate to pass it.**

That means no lowered thresholds, no new ignore/allowlist entries, no
`# noqa`, `# type: ignore`, `# pragma: no cover` added just to go green, and
no skipped or deleted tests. If a gate is genuinely wrong, say so in the pull
request and fix the gate itself in
[quality-zero-platform](https://github.com/Prekzursil/quality-zero-platform)
(see [Changing the gates](#changing-the-gates-operator-only)).

## Workflow

1. Branch from `main` (external contributors: fork first).
2. Make the change **together with the tests that exercise it** — in the same
   commit or pull request, never "tests later".
3. Run the gates locally (below) until every lane is green.
4. Open a pull request and fill in the checklist from the pull-request
   template; it maps 1:1 to what CI enforces.
5. Every required check must be green (`quality / quality`, `CodeQL`), the
   branch must be up to date with `main`, and every review conversation must
   be resolved before merging.

## The gates — zero tolerance

CI runs the QZP lean gate: `.github/workflows/quality.yml` calls
quality-zero-platform's `reusable-quality.yml`, pinned to an exact commit.
A finding of **any** severity fails the gate — there is no
"high and above only" floor anywhere. The dependency gate runs at
`deps-severity-floor: any`.

| Gate | What runs | Passes when |
| ---- | --------- | ----------- |
| 1 · Lint + format | ruff 0.15.17 (`ruff check`, `ruff format --check`) | zero findings |
| 2 · Types | basedpyright 1.39.8 (`standard`) on `swgb_save.py`, `swgb_save_gui.py` | zero errors, zero warnings |
| 3 · Tests + coverage | pytest 9.1.1 / pytest-cov 7.1.0 / coverage 7.16.2 | all tests pass at **100 % line AND branch** |
| 4 · SAST | opengrep v1.32.0 (curated `.quality/opengrep` ruleset) | zero findings |
| 5 · Secrets | gitleaks 8.30.1, whole tree, `--redact` | zero findings |
| 6 · Deps | osv-scanner v2.3.8 (`deps-severity-floor: any`) | zero findings of any severity |

On top of the lean gate:

- **CodeQL** (`.github/workflows/codeql.yml`, wrapper pinned to a QZP commit)
  scans `python` + `actions` on push, pull request and weekly. The repo's
  ruleset blocks any pull request that introduces a CodeQL alert of any
  severity (`alerts_threshold: all`).

## Running the gates locally

```bash
bash scripts/verify
```

`scripts/verify` runs QZP's preflight at the exact commit that
`.github/workflows/quality.yml` pins, so every CI lane runs locally with the
same pinned tool versions. Run it from this repository's root before every
push. A lane that cannot run locally (for example a missing toolchain) is
reported as `SKIP`, never as a silent pass — CI will still run it.

For quick iteration, the equivalent direct commands:

```bash
python -m pip install pytest pytest-cov ruff
python -m pytest --cov --cov-branch        # must end at 100.00% line and branch
python -m ruff check .
python -m ruff format --check .
```

## Coverage: 100 % line **and** branch, scope declared

Coverage is measured on every lane that has source code, and the bar is 100 %
of lines **and** 100 % of branches. Line-only 100 % is not enough: once
branches are counted, line-clean code typically sits at 99.x % and still
fails. Every new or changed line needs a test that executes it in the same
change.

Measured scope (see `pyproject.toml → [tool.coverage.run] source`):

- `swgb_save.py` — save-file decompress/compress and resource editing
- `swgb_save_gui.py` — the Tk editor front end

That pair is the repository's entire Python source; nothing ships unmeasured.
The only exclusion is the reasoned, greppable
`if __name__ == "__main__":` pragma in `[tool.coverage.report] exclude_also` —
the CLI/GUI entry points are exercised by the tests through their functions.

## Dependencies

This repository declares no third-party runtime dependencies: the app is
standard-library only, so there is no pip manifest tree for Dependabot to
track. The tracked manifest trees are:

- `.github/workflows/**` — `github-actions` rail (weekly)
- `.pre-commit-config.yaml` — `pre-commit` rail (weekly)

Minor and patch updates are grouped per ecosystem, security updates are
grouped so one pull request can clear every open advisory, and major updates
arrive one by one for review.

## Changing the gates (operator-only)

The quality lanes are **not** defined in this repository. They live in
[quality-zero-platform](https://github.com/Prekzursil/quality-zero-platform),
which governs every repository in the fleet:

- Gate changes happen in QZP, through a pull request — never by editing lanes
  here and never by weakening a check locally.
- This repository picks up a gate change when its `quality.yml` pin is bumped
  to the QZP commit that contains it.
- If a gate change turns this repository red, the fix belongs in the code (or,
  if the gate is wrong, in QZP) — not in a local exception.

## Code of conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
Reports go to the maintainer privately on GitHub (`@Prekzursil`).
