---
description: Weekly maintenance PR for the MLOps agentic workflow suite.
intent: Keep AGENTS.md and the daily-mlops-activity-report workflow accurate as the repository evolves; changes are proposed via pull request, never pushed to main directly.

on:
  schedule:
    # Weekly, Monday morning-ish. Uses gh-aw fuzzy schedule to jitter start
    # time and avoid load spikes.
    - cron: "weekly on monday"
  workflow_dispatch:

concurrency:
  group: mlops-workflow-maintainer
  cancel-in-progress: false

permissions:
  contents: read
  issues: read
  pull-requests: read
  actions: read
  copilot-requests: write

# Full checkout so the agent can read AGENTS.md and the workflow files it
# maintains, and so the create-pull-request safe output has a working tree
# to diff against.
checkout:
  - fetch-depth: 0

network:
  allowed:
    - defaults

tools:
  github:
    mode: gh-proxy
    toolsets: [default]

safe-outputs:
  report-failure-as-issue: true
  create-pull-request:
    title-prefix: "🧹 [maintainer] "
    labels: [mlops, maintenance, automated]
    draft: false
    max: 1
    allowed-files:
      - AGENTS.md
      - .github/workflows/daily-mlops-activity-report.md
---

# 🧹 MLOps Workflow Maintainer

You maintain the MLOps agentic-workflow suite in **`${{ github.repository }}`**.
Your job is to keep two artefacts accurate as the repository evolves:

1. `AGENTS.md` — the human-facing map of what agentic workflows exist here,
   what they do, when they run, and how a contributor changes them.
2. `.github/workflows/daily-mlops-activity-report.md` — the source of the
   daily digest workflow.

## Scope 📚

Read-only inspection of:

- Merged pull requests in the last 7 days.
- Any changes to `.github/workflows/` in that window.
- The current `AGENTS.md` (create it if missing).
- The current `daily-mlops-activity-report.md`.

## Decide 🧭

Open **exactly one** pull request when one or more of the following is true:

- `AGENTS.md` is missing, or is out of sync with the workflows actually
  present under `.github/workflows/`.
- The daily reporter's prompt references labels, cadence, or repositories
  that no longer match reality (e.g. new blocker labels widely used, new
  MLOps repos onboarded to this org).
- A commonly-used label appears in merged PRs but is not covered in the
  reporter's blocker rules.

If none of the above apply, emit `noop` with a one-sentence explanation.
A quiet week is a good week.

## Constraints 📏

- You may only modify these files (enforced by `create-pull-request.allowed-files`):
  - `AGENTS.md`
  - `.github/workflows/daily-mlops-activity-report.md`
- Do **not** modify `.lock.yml` files — a human will run
  `gh aw compile` on the merged branch.
- Keep every PR small: 1–2 files, focused explanation.
- PR body must include:
  - **Why**: the observation that triggered the change.
  - **What**: bulleted list of edits.
  - **Follow-up**: reminder to run `gh aw compile daily-mlops-activity-report`
    if the daily workflow was touched.

## Output ✍️

Emit **exactly one** `create_pull_request` tool call, or one `noop`.
No comments, no issues, no labels — just the PR (or the noop).
