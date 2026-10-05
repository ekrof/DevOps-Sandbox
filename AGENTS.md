# AGENTS.md

Map of the agentic workflows in this repository and how to change them.

## Agentic workflows (gh-aw)

| Workflow | Source | Trigger | What it does |
| --- | --- | --- | --- |
| Daily MLOps Activity Report | `.github/workflows/daily-mlops-activity-report.md` | Weekdays 07:00 UTC, manual | Rewrites a single pinned `daily-report` issue with new issues, in-progress items, opened/merged PRs and open blockers (`blocker`, `incident`, `priority/high`, `bug`). |
| MLOps Workflow Maintainer | `.github/workflows/mlops-workflow-maintainer.md` | Weekly (Monday), manual | Opens at most one PR that keeps `AGENTS.md` and the daily report prompt accurate. Limited to those two files. |

## Other (non-agentic) workflows

| Workflow | File | Trigger | Purpose |
| --- | --- | --- | --- |
| Assign Azure RBAC Roles | `.github/workflows/assign-azure-rbac.yaml` | Manual | Dispatch-form preview; makes no Azure calls. |
| Daily Report Preview | `.github/workflows/daily-report-preview.yml` | Weekdays 07:00 UTC, manual | LLM-free emulation of the daily report. |
| Generate CODEOWNERS | `.github/workflows/generate-codeowners.yaml` | Manual | Runs `generate-codeowners.sh`. |

## Changing an agentic workflow

1. Edit the `.md` source, never the `.lock.yml` file.
2. Run `gh aw compile <workflow-name>` and commit the regenerated `.lock.yml`.
3. Open a PR; the maintainer workflow also proposes drift fixes weekly.
