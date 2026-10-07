---
description: Daily activity report for AkerBP/dig-mlops-workspaces, delivered as a pinned issue.
intent: Give the DIG MLOps team one artefact per morning that surfaces what needs attention (bugs, review queue) plus new issues and opened/merged PRs in the workspaces repository.

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
  # statusCheckRollup includes check runs and legacy commit statuses.
  checks: read
  statuses: read
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

# Deterministic data gathering: exact counts and tables are computed here,
# the agent only reads the JSON and writes the narrative.
steps:
  - name: Gather report data
    env:
      GH_TOKEN: ${{ github.token }}
      # Read-only token for the org project (Projects v2 is not readable with
      # the default token). Optional: without it, only "updated in window" counts.
      PROJECT_TOKEN: ${{ secrets.GH_AW_READ_PROJECT_TOKEN }}
      REPO: ${{ github.repository }}
    run: |
      set -euo pipefail
      out=/tmp/gh-aw/agent
      mkdir -p "$out"

      now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      # Window start: 07:00 UTC of the previous weekday (Mon -> Fri).
      if [ "$(date -u +%u)" = "1" ]; then back="3 days ago"; else back="1 day ago"; fi
      since="$(date -u -d "$back" +%Y-%m-%dT07:00:00Z)"
      week_ago="$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)"
      stale_cut="$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)"

      report_number="$(gh issue list --repo "$REPO" --label daily-report \
        --state open --limit 1 --json number --jq '.[0].number // empty')"
      if [ -n "$report_number" ]; then
        gh issue view "$report_number" --repo "$REPO" --json body --jq .body \
          > "$out/previous-report.md"
      else
        : > "$out/previous-report.md"
      fi

      gh issue list --repo "$REPO" --state open --limit 300 \
        --json number,title,url,author,labels,assignees,createdAt,updatedAt \
        > "$out/issues-open.json"
      gh pr list --repo "$REPO" --state open --limit 200 \
        --json number,title,url,author,isDraft,createdAt,updatedAt,reviewDecision,reviewRequests,statusCheckRollup,closingIssuesReferences \
        > "$out/prs-open.json"
      gh pr list --repo "$REPO" --state merged --limit 200 \
        --search "merged:>=$week_ago" \
        --json number,title,url,author,createdAt,mergedAt \
        > "$out/prs-merged-7d.json"

      # Issue numbers whose Status is "In Progress" in org project 18 (read-only).
      echo '[]' > "$out/project-in-progress.json"
      if [ -n "${PROJECT_TOKEN:-}" ]; then
        GH_TOKEN="$PROJECT_TOKEN" gh api graphql --paginate -f query='
          query($endCursor:String){
            organization(login:"AkerBP"){ projectV2(number:18){
              items(first:100, after:$endCursor){
                pageInfo{hasNextPage endCursor}
                nodes{
                  status: fieldValueByName(name:"Status"){ ... on ProjectV2ItemFieldSingleSelectValue{ name } }
                  content{ ... on Issue{ number repository{ nameWithOwner } } }
                }}}}}' \
          --jq '.data.organization.projectV2.items.nodes[]
                | select(.status.name == "In Progress" and .content.number != null)
                | .content.number' \
          | jq -s . > "$out/project-in-progress.json" || echo '[]' > "$out/project-in-progress.json"
      fi

      # Branch status and other repo activity since the window start.
      default_branch="$(gh repo view "$REPO" --json defaultBranchRef --jq .defaultBranchRef.name)"
      gh api graphql --paginate -F owner="${REPO%/*}" -F name="${REPO#*/}" -f query='
        query($owner:String!, $name:String!, $endCursor:String){
          repository(owner:$owner, name:$name){
            refs(refPrefix:"refs/heads/", first:100, after:$endCursor){
              pageInfo{hasNextPage endCursor}
              nodes{ name target{ ... on Commit{ committedDate } } }}}}' \
        --jq '.data.repository.refs.nodes[] | {name, date: .target.committedDate}' \
        | jq -s --arg d "$default_branch" 'map(select(.name != $d))' > "$out/branches.json"
      main_commits="$(gh api "repos/$REPO/commits?sha=$default_branch&since=$since&per_page=100" --jq 'length')"
      jq -n --argjson c "${main_commits:-0}" '{main_commits:$c}' > "$out/activity.json"

      jq -n \
        --slurpfile br "$out/branches.json" \
        --slurpfile act "$out/activity.json" \
        --slurpfile proj "$out/project-in-progress.json" \
        --arg now "$now" --arg since "$since" --arg stale "$stale_cut" --arg week "$week_ago" \
        --arg report_number "$report_number" \
        --slurpfile issues "$out/issues-open.json" \
        --slurpfile prs "$out/prs-open.json" \
        --slurpfile merged "$out/prs-merged-7d.json" '
        def age_days: ((($now|fromdate) - (. | fromdate)) / 86400 | floor);
        def lbls: [.labels[].name];
        def active($ip; $new_nums): select((.updatedAt >= $since or (.number as $n | $ip | index($n))) and (.number as $n | $new_nums | index($n) | not));
        def ci:
          (.statusCheckRollup // []) as $c
          | if ($c|length) == 0 then "none"
            elif any($c[]; (.conclusion // "") as $k | $k=="FAILURE" or $k=="ERROR" or $k=="TIMED_OUT" or $k=="CANCELLED" or (.state // "")=="FAILURE" or (.state // "")=="ERROR") then "failing"
            elif any($c[]; ((.status // "COMPLETED") != "COMPLETED") or (.state // "")=="PENDING") then "pending"
            else "passing" end;
        def automated: (.title | test("^\\[Security\\] GitHub Actions workflow vulnerabilities|Workspace AD Group . Policy Violations"));
        def owners: (if (.assignees|length) > 0 then [.assignees[].login] else [.author.login] end);
        ($issues[0] | map(select(((lbls | index("daily-report")) | not) and (automated | not)))) as $is
        | ($prs[0]) as $ps
        | ($merged[0]) as $ms
        | ($is | map(select(.createdAt >= $since))) as $new_issues
        | ($new_issues | map(.number)) as $new_nums
        | ($proj[0]) as $ip
        | ($ms | map(select(.mergedAt >= $since))) as $merged_win
        | ($merged_win | map(.number)) as $merged_nums
        | {
            generated_at: $now,
            window: {since: $since, until: $now},
            report_issue_number: (if $report_number == "" then null else ($report_number|tonumber) end),
            bug_labels: ["bug"],
            new_issues: ($new_issues | map({number,title,url,owners:owners,labels:lbls})),
            in_progress: ($is | map(active($ip; $new_nums)) | map({number,title,url,owners:owners,updated_at:.updatedAt,labels:lbls})),
            prs_opened: ($ps | map(select(.createdAt >= $since)) | map({number,title,url,author:.author.login,draft:.isDraft})),
            prs_opened_total: (($ps | map(select(.createdAt >= $since)) | length) + ($merged_win | map(select(.createdAt >= $since)) | length)),
            prs_merged: ($merged_win | map({number,title,url,author:.author.login,merged_at:.mergedAt})),
            open_prs: ($ps | sort_by(.createdAt) | map({
                number,title,url,author:.author.login,draft:.isDraft,
                age_days:(.createdAt|age_days),
                review:(.reviewDecision // "NONE"),
                reviewers:[.reviewRequests[] | (.login // .name)],
                ci:ci,
                closes:[.closingIssuesReferences[].number],
                stale:(.updatedAt < $stale)
              })),
            workspace_requests: ($is | map(select(lbls | index("workspace-request"))) | map(
                .number as $n | {
                number,title,url,age_days:(.createdAt|age_days),
                linked_prs:[$ps[] | select(any(.closingIssuesReferences[]; .number == $n)) | .number]
              })),
            metrics: {
              new_issues: ($new_issues|length),
              in_progress: ($is | map(active($ip; $new_nums)) | length),
              prs_opened: ($ps | map(select(.createdAt >= $since)) | length),
              prs_total_incl_drafts: (($ps | map(select(.createdAt >= $since)) | length) + ($merged_win | map(select(.createdAt >= $since)) | length)),
              prs_merged: ($merged_win|length),
              open_bugs: ($is | map(select(lbls | index("bug"))) | length),
              open_prs: ($ps|length),
              median_open_pr_age_days: (if ($ps|length)==0 then null else ($ps | map(.createdAt|age_days) | sort | .[(length/2|floor)]) end),
              merged_last_7d: ($ms|length),
              branches_total: ($br[0]|length),
              branches_active: ($br[0] | map(select(.date >= $week)) | length),
              branches_stale: ($br[0] | map(select(.date < $week)) | length),
              branches_updated_in_window: ($br[0] | map(select(.date >= $since)) | length),
              main_commits: $act[0].main_commits
            }
          }' > "$out/report-data.json"

      # Azure Machine Learning updates from the last 7 days (they are infrequent; also covers weekends) (Azure release communications API).
      ml_since="$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)"
      curl -fsSL --max-time 30 -G "https://www.microsoft.com/releasecommunications/api/v2/azure" \
        --data-urlencode "\$filter=products/any(f:f eq 'Azure Machine Learning') and created ge $ml_since" \
        --data-urlencode '$orderby=created desc' --data-urlencode '$top=10' \
        | jq '[.value[] | {id,title,status,created,url:("https://azure.microsoft.com/updates?id=" + .id)}]' \
        > "$out/azure-ml-updates.json" || echo '[]' > "$out/azure-ml-updates.json"

      echo "Wrote $out/report-data.json"
      jq .metrics "$out/report-data.json"

safe-outputs:
  report-failure-as-issue: true
  # Bootstrap path: only used the very first time this workflow runs, when
  # no `daily-report`-labelled issue exists yet.
  create-issue:
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
          if ! err="$(gh api graphql -f query='
            mutation($id:ID!) {
              pinIssue(input:{issueId:$id}) { clientMutationId }
            }' -F id="$issue_id" 2>&1 >/dev/null)"; then
            if echo "$err" | grep -qi "already pinned"; then
              echo "Pin no-op (already pinned)."
            else
              echo "$err" >&2
              exit 1
            fi
          fi
---

## Daily MLOps Activity Report

You are the reporter for the AkerBP DIG MLOps team. Produce one concise,
friendly daily activity report for the repository this workflow runs in:
**`${{ github.repository }}`**.

This report lives in a **single persistent issue** that gets rewritten
every weekday — not a new issue per day.

## Data 🔎

A pre-step has already gathered and computed everything. **Do not recompute
counts or re-query GitHub for the lists below** — read these files and use
them as the single source of truth:

- `/tmp/gh-aw/agent/report-data.json` — all lists and metrics:
  `window`, `report_issue_number` (null on first-ever run), `new_issues`,
  `in_progress`, `prs_opened`, `prs_merged`, `open_prs`,
  `workspace_requests`, `metrics`.
- `/tmp/gh-aw/agent/azure-ml-updates.json` — Azure Machine Learning updates
  posted in the last 7 days (may be `[]`).
- `/tmp/gh-aw/agent/previous-report.md` — yesterday's report body (empty on
  first run), not needed.

Definitions (already applied in the data):

- **Window**: since 07:00 UTC of the previous weekday (Mondays → Friday).
- **In progress**: open issue that either has Status "In Progress" in the
  team project (read-only) or was updated inside the window, and is not in
  `new_issues` (an issue never appears in both lists).
- **Branch**: non-default branch. Active = last commit within 7 days; stale =
  older. Counts only, taken from `metrics`.
- **Bug**: open issue labelled `bug`, regardless of update time. Only a count
  in metrics.
- Automated issues (security scan, AD group violations) are already filtered
  out of the data. Do not surface them.
- **Owner**: assignees; falls back to the issue creator if unassigned.

Call `noop` only if every list is empty **and** `report_issue_number` is null.
Otherwise always write the report.



## Output — required tool calls, in order ✍️

**Step 1 — create or update the report issue** (exactly one of the two).
The title is always exactly `🌅 Daily MLOps Activity Report` (no date, no
prefix):

- `report_issue_number` is null → `create_issue` once.
- Otherwise → `update_issue` once with `issue_number` =
  `report_issue_number`, `operation: "replace"`, `status: "open"`, the same
  title, and the new body.

Body template. **The issue title already says "Daily MLOps Activity Report",
so do not add a top-level heading with that name.** Omit any section marked
_(omit if empty)_ when its list is empty.

```markdown
## ☀️ Good morning, MLOps crew!

### 🧭 TL;DR
- <2–6 actionable bullets, most urgent first: PRs without reviewers, aging PRs, bugs. No filler such as "quiet day".>

## 📚 Activity digest

**🆕 New issues (N)** _(omit if empty)_
- <link> <title> — @owner(s), labels: `bug`, `mlops`

**🔧 In-progress (N)** _(omit if empty)_
- <link> <title> — @owner(s), updated <relative time>

**🚀 Pull requests opened (N)** _(omit if empty)_
- <link> <title> — @author (draft/ready)

**✅ Pull requests merged (N)** _(omit if empty)_
- <link> <title> — @author, merged <relative time>

**🏗️ Workspace requests (N)** _(omit if empty)_
- <link> <title> — age, linked PR(s) or "no PR yet"

## 🔀 Open pull requests (N)
| # | Title | Author | Age | State | Review | CI | Reviewers |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 📊 Metrics
- 🆕 New issues: N · 🔧 In progress: N
- 🚀 PRs opened: N (incl. same-window merges: N) · ✅ PRs merged: N
- 🔀 Open PRs: N · median open-PR age: Nd · merged last 7 days: N
- 🐞 Open bugs: N
- 🌿 Branches: N (active N · stale N) · pushed in window: N
- 📝 Commits on default branch in window: N

## 📰 Azure ML news (last 7 days) _(omit if `azure-ml-updates.json` is empty)_
- [<title>](<url>) — <status; drop " — <status>" if null>

_Last updated: <DD.MM.YYYY HH:MM> · Report window: <DD.MM.YYYY HH:MM> → <DD.MM.YYYY HH:MM>_
```

Table/section rules:

- **Open pull requests**: list every item in `open_prs`, oldest first. State =
  `draft`/`ready`. Review = `approved`, `changes requested`, `review required`
  or `none` (map `APPROVED`, `CHANGES_REQUESTED`, `REVIEW_REQUIRED`; empty or `NONE` → `none`).
  CI = ✅ passing, ❌ failing, ⏳ pending, `–` none. Reviewers = requested
  reviewers as backticked GitHub handles, e.g. `@maxrodca` `@other`, or `none`. Mark PRs with no reviewers or review required and
  age ≥ 3d with ⚠️ in the Review cell. If empty write `_No open PRs._`.

## Rules 📏

- Keep the whole body under ~400 lines. Truncate titles at 80 chars.
- Every issue and PR reference is a markdown link with its full URL from the
  data, e.g. `[#123](https://github.com/...)`.
- Use the emojis exactly as shown so the layout stays consistent across days.
- Plain `@user` handles, except the PR Reviewers column (backticked).
- Never put a date in the issue **title**; only in the `_Last updated:_` line.
- **Timestamps**: all dates/times in European format, 24-hour clock,
  converted to Europe/Oslo local time — `DD.MM.YYYY HH:MM`, no timezone
  abbreviation. Keep "Last updated" and "Report window" on one line, at the very bottom of the body.
- **Relative times**: whole units only, no decimals. Under 1 hour → minutes
  (`23m ago`); hours → nearest hour (`18h ago`); days → nearest day (`2d ago`).
- Metric numbers come from `metrics` verbatim.
- **Step 2 — `pin_daily_report`** (exactly once, immediately after step 1
  succeeds) with any short `note`. Mandatory; no-op if already pinned.
- Emit **exactly one** `create_issue` **or** `update_issue` call, followed by
  **exactly one** `pin_daily_report` call. No comments, labels, PRs, or other
  side effects.
- Body must be between 20 and 65 000 characters (safe-outputs constraint).
