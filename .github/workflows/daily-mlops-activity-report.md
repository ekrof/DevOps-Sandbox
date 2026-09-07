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
  create-issue:
    title-prefix: "🌅 [Daily MLOps Activity] "
    labels: [mlops, daily-report, automated]
    max: 1
    # Replace-previous-result strategy: latest report supersedes older ones.
    close-older-issues: true
    deduplicate-by-title: true
  # Custom safe-output job. `needs: safe_outputs` (persists across
  # recompiles, per gh-aw docs) guarantees this runs AFTER the create-issue
  # handler above, so the issue already exists when this job looks for it.
  # This is an agent-invoked MCP tool — the agent must call `pin_daily_report`
  # explicitly (see the prompt body's final instruction) for this job to run
  # at all; it is not automatic just because create_issue ran.
  jobs:
    pin_daily_report:
      description: "Pin today's activity report issue and unpin any previous pinned report. Call this exactly once, immediately after create_issue succeeds."
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
      - name: Unpin previous daily report and pin the new one
        env:
          GITHUB_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
        run: |
          set -euo pipefail

          owner="${REPO%/*}"
          name="${REPO#*/}"

          # 1. Find the newest open issue carrying the `daily-report` label —
          #    that's the one the create-issue safe output just filed.
          new_number="$(gh issue list --repo "$REPO" \
            --label daily-report --state open \
            --limit 1 --json number --jq '.[0].number')"

          if [ -z "$new_number" ] || [ "$new_number" = "null" ]; then
            echo "No open daily-report issue found — nothing to pin."
            exit 0
          fi

          new_id="$(gh api graphql -f query='
            query($owner:String!, $name:String!, $number:Int!) {
              repository(owner:$owner, name:$name) {
                issue(number:$number) { id }
              }
            }' -F owner="$owner" -F name="$name" -F number="$new_number" \
            | jq -r '.data.repository.issue.id')"

          # 2. Unpin any currently-pinned issues carrying the `daily-report`
          #    label so we never keep more than one pinned report.
          pinned_json="$(gh api graphql -f query='
            query($owner:String!, $name:String!) {
              repository(owner:$owner, name:$name) {
                pinnedIssues(first: 3) {
                  nodes { issue { id number labels(first:20){nodes{name}} } }
                }
              }
            }' -F owner="$owner" -F name="$name")"

          echo "$pinned_json" \
            | jq -r --arg keep "$new_id" '
                .data.repository.pinnedIssues.nodes[]
                | select(.issue.labels.nodes | map(.name) | index("daily-report"))
                | select(.issue.id != $keep)
                | .issue.id' \
            | while read -r old_id; do
                [ -n "$old_id" ] || continue
                echo "Unpinning issue node $old_id"
                gh api graphql -f query='
                  mutation($id:ID!) {
                    unpinIssue(input:{issueId:$id}) { clientMutationId }
                  }' -F id="$old_id" >/dev/null
              done

          # 3. Pin the new issue (idempotent — GitHub errors if already pinned,
          #    which we swallow).
          echo "Pinning new issue #$new_number (node $new_id)"
          gh api graphql -f query='
            mutation($id:ID!) {
              pinIssue(input:{issueId:$id}) { clientMutationId }
            }' -F id="$new_id" >/dev/null || \
            echo "Pin no-op (likely already pinned)."
---

# 🌅 Daily MLOps Activity Report

You are the reporter for the AkerBP DIG MLOps team. Produce one concise,
friendly daily activity report for the repository this workflow runs in:
**`${{ github.repository }}`**.

## Time window ⏰

- **Since**: the previous scheduled run of this workflow. On Mondays that means
  since Friday 07:00 UTC; on other weekdays, the last 24 hours.
- **"In progress"** = an issue or PR that is open **and** has been updated
  inside the time window.
- **"Blocker"** = any open issue or PR labelled `blocker`, `incident`,
  `priority/high`, or `bug`, regardless of update time.

## Data to gather (read-only, via the `github` gh-proxy toolset) 🔎

Using `gh` commands against the current repository only:

1. **New issues opened in the window** — number, title, author, labels.
2. **In-progress tasks** — open issues updated inside the window: number, title,
   assignees, last-updated-at, current labels.
3. **Pull requests opened in the window** — number, title, author, draft flag.
4. **Pull requests merged in the window** — number, title, author, merge time.
5. **Open blockers** — every open issue or PR matching the blocker rule above,
   with age.

Do not attempt to clone code. Do not attempt to read other repositories. Call
`noop` only if every list above is empty, with a short explanation.

## Output — two required tool calls, in order ✍️

**Step 1 — `create_issue`** (exactly once):

- **Title**: `Daily MLOps Activity — <YYYY-MM-DD>` (UTC date of the run).
  The `title-prefix` in frontmatter automatically prepends `🌅 [Daily MLOps
  Activity] `, so keep the title itself emoji-free.
- **Body**: Markdown, in this exact structure. Emit `_none_ 🎉` for empty
  sections (a quiet day is a good day).

```
## ☀️ Good morning, MLOps crew!

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

**Step 2 — `pin_daily_report`** (exactly once, immediately after `create_issue`
succeeds):

Call the `pin_daily_report` tool with any short `note` (e.g. `"pin today's
report"`). This is **mandatory**, not optional — it is what pins the new
issue and unpins yesterday's. Skipping this call means the report is
created but never pinned.

## Rules 📏

- Keep the whole body under ~400 lines. Truncate titles at 80 chars.
- Every issue and PR reference must be a full URL (`https://github.com/...`).
- Use the emojis exactly as shown in the template so the layout stays
  consistent across days.
- Emit **exactly one** `create_issue` call followed by **exactly one**
  `pin_daily_report` call. No comments, no labels, no PRs, no other side
  effects.
- If you call `noop` instead of `create_issue` (empty report), do **not**
  call `pin_daily_report` — there is nothing new to pin.
- Body must be between 20 and 65 000 characters (safe-outputs constraint).
