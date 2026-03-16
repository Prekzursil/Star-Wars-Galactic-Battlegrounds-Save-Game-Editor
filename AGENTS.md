# AGENTS.md

## Operating Model

This repository uses shared `quality-zero-platform` wrapper workflows for strict-zero quality automation.
Keep changes evidence-backed, small, and task-focused.

## Canonical Verification Command

Run this command before claiming completion:

```bash
bash scripts/verify
```

## Scope Guardrails

- Do not commit secrets or local runtime artifacts.
- Prefer tests/docs updates together with behavior changes.
- Treat missing external statuses as policy drift before code changes.

## Agent Queue Contract
- Intake issues via `.github/ISSUE_TEMPLATE/agent_task.yml`.
- Queue work by adding `agent:ready` label.
- Queue workflow will post a task packet and notify `@copilot`.

## Queue Trigger Warning
> ⚠️ Applying label `agent:ready` triggers the queue workflow **immediately**.
> The queue is idempotent: if an Execution Contract comment already exists on the issue,
> no further label mutations occur and no duplicate comment is posted.
> Removing and re-adding the label after a contract exists will have no effect.