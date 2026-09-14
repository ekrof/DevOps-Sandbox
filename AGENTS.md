# AGENTS.md — MLOps Agentic Workflow Suite

This file maps the agentic (Copilot-in-Actions) workflows and the
conventional GitHub Actions workflows that live in `.github/workflows/` of
**`ekrof/DevOps-Sandbox`**, so contributors know what runs, when, and how to
change it safely.

## Agentic workflows (gh-aw, Copilot-in-Actions)

These are authored as Markdown + frontmatter (`*.md`) and compiled to a
matching `*.lock.yml` via `gh aw compile`. **Never hand-edit a `.lock.yml`
file** — always edit the `.md` source and recompile.

### `daily-mlops-activity-report.md`

- **Purpose**: Posts/refreshes a single pinned issue in this repository
  each weekday morning summarizing new issues, in-progress work,
  opened/merged PRs, and open blockers.
- **Trigger**: `schedule` (`0 7 * * 1-5`, weekdays 07:00 UTC) and
  `workflow_dispatch`.
- **Scope**: Read-only against `${{ github.repository }}` only, via the
  `github` gh-proxy toolset. No checkout.
- **Blocker labels covered**: `blocker`, `incident`, `priority/high`, `bug`.
- **Safe outputs**: `create-issue` (bootstrap only, labels
  `mlops, daily-report, automated`), `update-issue` (steady-state rewrite),
  and a custom `pin_daily_report` job that pins the report issue.
- **To change**: edit `daily-mlops-activity-report.md`, then run
  `gh aw compile daily-mlops-activity-report` to refresh the `.lock.yml`.

### `mlops-workflow-maintainer.md` (this workflow)

- **Purpose**: Weekly self-maintenance — keeps this file (`AGENTS.md`) and
  the daily reporter's prompt in sync with reality, proposed via PR.
- **Trigger**: `schedule` (`weekly on monday`, gh-aw fuzzy schedule) and
  `workflow_dispatch`.
- **Scope**: Read-only inspection of merged PRs (last 7 days), changes
  under `.github/workflows/`, `AGENTS.md`, and
  `daily-mlops-activity-report.md`.
- **Safe outputs**: `create-pull-request` (labels
  `mlops, maintenance, automated`, max 1), restricted via
  `allowed-files` to `AGENTS.md` and
  `.github/workflows/daily-mlops-activity-report.md` only.
- **To change**: edit `mlops-workflow-maintainer.md`, then run
  `gh aw compile mlops-workflow-maintainer` to refresh the `.lock.yml`.

## Conventional GitHub Actions workflows

### `assign-azure-rbac.yaml`

- **Purpose**: On-demand Azure RBAC role assignment (Foundry User,
  Cognitive Services OpenAI User, Search Index Data Contributor, Search
  Service Contributor) for a service principal in `dev`/`test`/`prod`, with
  a `dry_run` preview option. Syncs current assignments to a pinned
  `rbac-state`-labelled issue after each run.
- **Trigger**: `workflow_dispatch` only.
- **Auth**: Azure OIDC login (`azure/login@v2`).

### `generate-codeowners.yaml`

- **Purpose**: Regenerates the `CODEOWNERS` file from repository rules and
  commits the update if it changed.
- **Trigger**: `workflow_dispatch` only.

## Conventions for contributors

- Agentic workflow sources are the `*.md` files; the paired `*.lock.yml`
  is a generated build artifact — regenerate it with `gh aw compile
  <workflow-name>` after any `.md` edit, don't edit it by hand.
- The `mlops-workflow-maintainer` workflow keeps this file and the daily
  reporter's prompt current automatically; if you add, remove, or
  materially change a workflow under `.github/workflows/`, expect (or
  manually trigger) a follow-up maintenance PR the next time it runs.
