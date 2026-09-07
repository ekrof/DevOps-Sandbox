# AGENTS.md — MLOps Agentic Workflows Map

This file is the human-facing map of the agentic (Copilot-powered) workflows
that live in `.github/workflows/` in this repository. It is kept in sync by
the `mlops-workflow-maintainer` workflow itself — if you add, remove, or
meaningfully change an agentic workflow, expect (or trigger) a maintenance
PR that updates this file.

## What's here

| Workflow file | Source (`.md`) | Trigger | Purpose |
| --- | --- | --- | --- |
| `daily-mlops-activity-report.lock.yml` | `daily-mlops-activity-report.md` | Weekdays 07:00 UTC + manual dispatch | Posts/updates a single pinned issue summarizing new issues, in-progress work, opened/merged PRs, and open blockers for this repo. |
| `mlops-workflow-maintainer.lock.yml` | `mlops-workflow-maintainer.md` | Weekly (Monday, fuzzy schedule) + manual dispatch | Reviews the last 7 days of activity and opens a PR to keep this file and the daily reporter's prompt accurate. |

Non-agentic workflows in this repo (not covered by this map, no Copilot
inference involved):

- `assign-azure-rbac.yaml` — manual dispatch to assign Azure RBAC roles to a
  service principal per environment (dev/test/prod).
- `generate-codeowners.yaml` — manual dispatch that regenerates `CODEOWNERS`
  from `generate-codeowners.sh` and auto-commits if it changed.

## How the agentic workflows work

Both agentic workflows are defined as **markdown prompt + YAML frontmatter**
files (the `.md` files above) and compiled with [`gh aw`](https://github.com/githubnext/gh-aw)
into the corresponding `.lock.yml` GitHub Actions workflow. **Never hand-edit
a `.lock.yml` file** — edit the `.md` source and recompile.

- **`daily-mlops-activity-report.md`**: read-only (`checkout: false`), uses
  the `gh-proxy` GitHub toolset to gather issues/PRs via `gh`, then either
  `create-issue` (first run) or `update-issue` (every subsequent run) to
  rewrite a single pinned `daily-report`-labelled issue. A custom
  `pin_daily_report` safe-output job pins that issue after it's created or
  updated.
- **`mlops-workflow-maintainer.md`** (this workflow): full checkout
  (`fetch-depth: 0`), read-only inspection of merged PRs, `.github/workflows/`
  changes, `AGENTS.md`, and the daily reporter's prompt. It may open **at
  most one** pull request per run, restricted by `allowed-files` to:
  - `AGENTS.md`
  - `.github/workflows/daily-mlops-activity-report.md`

  If nothing needs to change, it emits a `noop` instead of a PR.

## Making changes

1. Edit the relevant `.md` source file (never the `.lock.yml`).
2. Run `gh aw compile <workflow-name>` to regenerate the `.lock.yml`.
3. Commit both the `.md` and the regenerated `.lock.yml` together.
4. If you change labels, cadence, or repositories referenced by the daily
   reporter, update this file's table/description to match.

## Current blocker-label rule (daily reporter)

The daily reporter currently treats any open issue/PR labelled `blocker`,
`incident`, `priority/high`, or `bug` as a blocker. This repository's label
set (`bug`, `documentation`, `enhancement`, `good first issue`,
`help wanted`, `invalid`, `question`, `wontfix`, `security fix`,
`security vulnerability`, `Mend: configuration error`, `rbac-state`,
`automated`, `daily-report`, `mlops`) does not currently use `blocker`,
`incident`, or `priority/high`, so only `bug` is actively matched. Revisit
this rule if new priority/incident labels are introduced.
