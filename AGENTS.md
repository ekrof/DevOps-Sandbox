# AGENTS.md

This file is the human-facing map of the agentic and automated workflows
that live under `.github/workflows/` in this repository. It is kept in
sync by the `mlops-workflow-maintainer` agentic workflow, which opens a
pull request whenever the workflow suite drifts out of date with this
document.

## Agentic (Copilot / gh-aw) workflows

These workflows are defined by a `.md` source file plus a compiled
`.lock.yml` (generated via `gh aw compile`). Never edit the `.lock.yml`
files by hand — edit the `.md` source and recompile.

### `daily-mlops-activity-report`

- **Source**: `.github/workflows/daily-mlops-activity-report.md`
- **Runs**: weekdays at 07:00 UTC (`cron: "0 7 * * 1-5"`), plus manual
  `workflow_dispatch`.
- **What it does**: Reads the current repository's issues and PRs
  (read-only, via the `github` gh-proxy toolset) and produces one
  concise daily activity report, delivered as a single pinned issue that
  is rewritten in place every run (never a new issue per day). It
  reports new issues, in-progress activity, opened/merged PRs, and open
  blockers (issues/PRs labelled `blocker`, `incident`, `priority/high`,
  or `bug`).
- **How to change it**: Edit the `.md` source, then run
  `gh aw compile daily-mlops-activity-report` and commit the regenerated
  `.lock.yml` alongside your change.

### `mlops-workflow-maintainer`

- **Source**: `.github/workflows/mlops-workflow-maintainer.md`
- **Runs**: weekly, Monday morning (fuzzy `gh-aw` schedule), plus manual
  `workflow_dispatch`.
- **What it does**: Inspects merged PRs from the last 7 days and any
  recent changes to `.github/workflows/`, then checks whether this
  `AGENTS.md` file and the daily reporter's prompt are still accurate.
  If drift is found, it opens exactly one pull request (limited to
  editing `AGENTS.md` and `daily-mlops-activity-report.md`). If nothing
  has drifted, it emits a `noop`.
- **How to change it**: Edit the `.md` source, then run
  `gh aw compile mlops-workflow-maintainer` and commit the regenerated
  `.lock.yml` alongside your change.

## Plain GitHub Actions workflows

These are conventional YAML workflows, not agentic/Copilot-driven.

### `assign-azure-rbac.yaml`

- **Trigger**: manual `workflow_dispatch` only.
- **What it does**: Assigns Azure RBAC roles (Foundry User, Cognitive
  Services OpenAI User, Search Index Data Contributor, Search Service
  Contributor) to a target service principal in a chosen environment
  (`dev`/`test`/`prod`), with an optional `dry_run` preview mode.
- **How to change it**: Edit the YAML directly; no compile step needed.

### `generate-codeowners.yaml`

- **Trigger**: manual `workflow_dispatch` only.
- **What it does**: Regenerates the `CODEOWNERS` file from
  `generate-codeowners.sh` using the configured organization/team
  defaults, and auto-commits the result if it changed.
- **How to change it**: Edit the YAML directly; no compile step needed.

## Keeping this file accurate

If you add, remove, or materially change a workflow under
`.github/workflows/`, either update this file yourself in the same PR,
or let the weekly `mlops-workflow-maintainer` workflow catch the drift
and propose the update automatically.
