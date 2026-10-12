# AGENTS.md

Map of the workflows under `.github/workflows/` in this repository.

## Agentic workflows (gh-aw)

Source is the `.md` file; the `.lock.yml` is generated. After editing a `.md`
file, run `gh aw compile <name>` and commit the regenerated lock file.

| Workflow | Source | Trigger | Purpose |
|---|---|---|---|
| Daily MLOps activity report | `daily-mlops-activity-report.md` | Weekdays 07:00 UTC (`0 7 * * 1-5`), manual | Gathers issues, PRs, project status, bugs, review queue, branch activity and ML news, and publishes a daily report issue (label `daily-report`). Read-only agent. |
| MLOps workflow maintainer | `mlops-workflow-maintainer.md` | Weekly (Monday, fuzzy), manual | Keeps `AGENTS.md` and the daily report source accurate by opening at most one small PR (`mlops`, `maintenance`, `automated` labels). |

## Plain GitHub Actions workflows

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| Daily Report Preview | `daily-report-preview.yml` | Weekdays 07:00 UTC, manual | Non-LLM emulation of the daily report data gathering. |
| Assign Azure RBAC Roles | `assign-azure-rbac.yaml` | Manual | Dispatch-form preview of the workflow in AkerBP/dig-ai-foundation; makes no Azure calls. |
| Generate CODEOWNERS | `generate-codeowners.yaml` | Manual | Runs `generate-codeowners.sh` after `install-tools.sh`. |

## Changing a workflow

1. Edit the `.md` source (frontmatter for triggers, permissions and safe outputs; body for the prompt).
2. Run `gh aw compile <workflow-name>` to regenerate the `.lock.yml`.
3. Open a PR; do not push to the default branch directly.
4. Update this file whenever a workflow is added, removed, or its trigger changes.
