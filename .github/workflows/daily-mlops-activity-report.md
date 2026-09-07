---
description: Daily activity report for AkerBP/dig-mlops-workspaces, delivered as a pinned issue.
intent: Give the DIG MLOps team one artefact per morning that surfaces new issues, in-progress activity, opened/merged PRs, and open blockers in the workspaces repository.

on:
  schedule:
    # 07:00 UTC weekdays == 08:00 (winter) / 09:00 (summer) Europe/Oslo.
    - cron: "0 7 * * 1-5"
  workflow_dispatch:

concurrency:
  group: daily-mlops-activity-report
  cancel-in-progress: false

# Agent stays read-only. Copilot inference uses the built-in Actions token
# via `copilot-requests: write` — no PAT required. If Copilot-in-Actions is
# governance-locked at the org level, swap `engine:` to `claude` or `codex`
# (see ../README.md for the fallback recipe).
permissions:
  contents: read
  issues: read
  pull-requests: read
  actions: read
  copilot-requests: write

# No local checkout is needed — everything comes from the GitHub API.
checkout: false

network:
  allowed:
    - defaults

# Single-repo scope: the default GITHUB_TOKEN reads the current repo. No
# extra secrets, no PAT, no GitHub App required.
tools:
  github:
    mode: gh-proxy
    toolsets: [default]

safe-outputs:
  report-failure-as-issue: true
  # Bootstrap path: only used the very first time this workflow runs, when
  # no `daily-report`-labelled issue exists yet.
  create-issue:
    title-prefix: "🌅 [Daily MLOps Activity] "
    labels: [mlops, daily-report, automated]
    max: 1
  # Steady-state path: every subsequent run rewrites the same issue in
  # place instead of creating a new one. `target: "*"` requires the agent
  # to supply issue_number (discovered via gh issue list in the prompt).
  update-issue:
    status:
    title:
    body:
    target: "*"
    max: 1
  # Custom safe-output job. `needs: safe_outputs` (persists across
  # recompiles, per gh-aw docs) guarantees this runs AFTER the
  # create-issue/update-issue handlers above. This is an agent-invoked MCP
  # tool — the agent must call `pin_daily_report` explicitly (see the
  # prompt body's final instruction) for this job to run at all.
  jobs:
    pin_daily_report:
      description: "Pin the single persistent activity report issue. Call this exactly once, after create_issue or update_issue succeeds."
      needs: safe_outputs
      runs-on: ubuntu-latest
      permissions:
        contents: read
        issues: write
      inputs:
        note:
          description: "Optional short note (ignored by the job, present only to satisfy the tool schema)"
          required: false
          type: string
      steps:
      - name: Pin the daily report issue if not already pinned
        env:
          GITHUB_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
        run: |
          set -euo pipefail

          owner="${REPO%/*}"
          name="${REPO#*/}"

          # There is only ever one daily-report issue (create-issue bootstraps
          # it once; every later run rewrites it via update-issue), so we just
          # need to find it and make sure it's pinned. No unpinning of
          # "older" reports is needed since there is nothing else to unpin.
          issue_number="$(gh issue list --repo "$REPO" \
            --label daily-report --state open \
            --limit 1 --json number --jq '.[0].number')"

          if [ -z "$issue_number" ] || [ "$issue_number" = "null" ]; then
            echo "No open daily-report issue found — nothing to pin."
            exit 0
          fi

          issue_id="$(gh api graphql -f query='
            query($owner:String!, $name:String!, $number:Int!) {
              repository(owner:$owner, name:$name) {
                issue(number:$number) { id }
              }
            }' -F owner="$owner" -F name="$name" -F number="$issue_number" \
            | jq -r '.data.repository.issue.id')"

          echo "Pinning issue #$issue_number (node $issue_id)"
          gh api graphql -f query='
            mutation($id:ID!) {
              pinIssue(input:{issueId:$id}) { clientMutationId }
            }' -F id="$issue_id" >/dev/null || \
            echo "Pin no-op (likely already pinned)."
---

# 🌅 Daily MLOps Activity Report

You are the reporter for the AkerBP DIG MLOps team. Produce one concise,
friendly daily activity report for the repository this workflow runs in:
**`${{ github.repository }}`**.

This report lives in a **single persistent issue** that gets rewritten
every weekday — not a new issue per day. Before writing anything, find out
whether that issue already exists.

## Time window ⏰

- **Since**: the previous scheduled run of this workflow. On Mondays that means
  since Friday 07:00 UTC; on other weekdays, the last 24 hours.
- **"In progress"** = an issue or PR that is open **and** has been updated
  inside the time window.
- **"Blocker"** = any open issue or PR labelled `blocker`, `incident`,
  `priority/high`, or `bug`, regardless of update time.

## Data to gather (read-only, via the `github` gh-proxy toolset) 🔎

Using `gh` commands against the current repository only:

0. **Find the existing report issue** — search for an open issue labelled
   `daily-report` (e.g. `gh issue list --label daily-report --state open`).
   Remember its number if found; if none exists, this is the first-ever run.
1. **New issues opened in the window** — number, title, author, labels.
2. **In-progress tasks** — open issues updated inside the window: number, title,
   assignees, last-updated-at, current labels.
3. **Pull requests opened in the window** — number, title, author, draft flag.
4. **Pull requests merged in the window** — number, title, author, merge time.
5. **Open blockers** — every open issue or PR matching the blocker rule above,
   with age.

Do not attempt to clone code. Do not attempt to read other repositories. Call
`noop` only if every list above is empty, with a short explanation — even on
a quiet day, still update the existing report issue if one exists (see below);
only skip entirely if there is truly nothing to say AND no report issue
exists yet.

## Output — required tool calls, in order ✍️

**Step 1 — create or update the report issue** (exactly one of the two):

- **If step 0 found no existing `daily-report` issue** (first-ever run),
  call `create_issue` once:
  - **Title**: `Daily MLOps Activity Report` (static — never include a date;
    the `title-prefix` in frontmatter prepends `🌅 [Daily MLOps Activity] `
    automatically).
  - **Body**: the template below.
- **If step 0 found an existing `daily-report` issue**, call `update_issue`
  once instead, targeting that `issue_number`, with `operation: "replace"`
  and:
  - **status**: `"open"` (always keep it open).
  - **title**: the same static title as above (do not change it).
  - **body**: the template below, fully replacing the previous content.

Body template (identical for both create and update):

```
## ☀️ Good morning, MLOps crew!

_Last updated: <current UTC timestamp>_
_Report window: <start UTC> → <end UTC>_

## 🧭 TL;DR
- <3–6 bullets highlighting what needs the team's attention today>

## 🚨 Open blockers
| # | Title | Age | Labels |
| --- | --- | --- | --- |

## 📚 Activity digest

**🆕 New issues (N)**
- #123 <title> — @author, labels: `bug`, `mlops`

**🔧 In-progress (N)**
- #124 <title> — @assignee, updated <relative time>

**🚀 Pull requests opened (N)**
- #125 <title> — @author (draft/ready)

**✅ Pull requests merged (N)**
- #126 <title> — @author, merged <relative time>

## 📊 Metrics
- 🆕 New issues total: N
- 🔧 In-progress items total: N
- 🚀 PRs opened total: N
- ✅ PRs merged total: N
- 🚨 Open blockers total: N

---
_🤖 Auto-generated by the `daily-mlops-activity-report` agentic workflow._
_Have a productive day! ☕_
```

**Step 2 — `pin_daily_report`** (exactly once, immediately after step 1
succeeds):

Call the `pin_daily_report` tool with any short `note` (e.g. `"pin the
report"`). This is **mandatory**, not optional — it ensures the report
issue stays pinned. Safe to call every run; it is a no-op if already pinned.

## Rules 📏

- Keep the whole body under ~400 lines. Truncate titles at 80 chars.
- Every issue and PR reference must be a full URL (`https://github.com/...`).
- Use the emojis exactly as shown in the template so the layout stays
  consistent across days.
- Never put a date in the issue **title** — only in the `_Last updated:_`
  line inside the body. The title must stay identical across every run so
  step 0's search keeps finding the same issue.
- Emit **exactly one** `create_issue` **or** `update_issue` call (never
  both), followed by **exactly one** `pin_daily_report` call. No comments,
  no labels, no PRs, no other side effects.
- Body must be between 20 and 65 000 characters (safe-outputs constraint).
