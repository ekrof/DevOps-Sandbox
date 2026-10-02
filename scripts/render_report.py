#!/usr/bin/env python3
"""Deterministic emulation of the agent-written daily report (no LLM)."""
import json, re, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

data = json.load(open(sys.argv[1]))
prev = open(sys.argv[2]).read() if len(sys.argv) > 2 else ""
legacy = "--legacy" in sys.argv
OSLO = ZoneInfo("Europe/Oslo")
now = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))


def ts(s):
    d = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(OSLO)
    return d.strftime("%d.%m.%Y %H:%M")


def rel(s):
    sec = (now - datetime.fromisoformat(s.replace("Z", "+00:00"))).total_seconds()
    if sec < 3600:
        return f"{round(sec / 60)}m ago"
    if sec < 86400:
        return f"{round(sec / 3600)}h ago"
    return f"{round(sec / 86400)}d ago"


def link(i):
    return f"[#{i['number']}]({i['url']})"


def t(s, n=80):
    return s if len(s) <= n else s[: n - 1] + "…"


def lbl(ls):
    return ", ".join(f"`{x}`" for x in ls) or "–"


def at(u):
    return f"@{u}"


m = data["metrics"]
w = data["window"]
out = []
header = (f"_Last updated: {ts(data['generated_at'])} · "
          f"Report window: {ts(w['since'])} → {ts(w['until'])}_")

if legacy:
    old_blockers = [b for b in data["blockers"] if "bug" in b["labels"]]
    out += ["## 🌅 Daily MLOps Activity Report", "", "☀️ Good morning, MLOps crew!", "", header, "",
            "## 🧭 TL;DR", f"- {m['new_issues']} new issues, {m['prs_opened']} PRs opened, "
            f"{len(old_blockers)} open blockers. A quiet start.", "",
            "## 📚 Activity digest", "", "**🚨 Open blockers**",
            "| # | Title | Age | Labels |", "| --- | --- | --- | --- |"]
    for b in old_blockers:
        out.append(f"| {link(b)} | {t(b['title'])} | {b['age_days']}d ago | {lbl(b['labels'])} |")
    out += ["", f"**🆕 New issues ({len(data['new_issues'])})**"]
    out += [f"- {link(i)} {t(i['title'])} — ``{at(i['author'])}``, labels: {lbl(i['labels'])}"
            for i in data["new_issues"]] or ["- _None opened in this window._"]
    out += ["", f"**🔧 In-progress ({len(data['in_progress'])})**"]
    out += [f"- {link(i)} {t(i['title'])} — ``{at(i['assignees'][0]) if i['assignees'] else 'unassigned'}``, "
            f"updated {rel(i['updated_at'])}" for i in data["in_progress"]] or ["- _None._"]
    out += ["", f"**🚀 Pull requests opened ({len(data['prs_opened'])})**"]
    out += [f"- {link(p)} {t(p['title'])} — ``{at(p['author'])}`` ({'draft' if p['draft'] else 'ready'})"
            for p in data["prs_opened"]] or ["- _None._"]
    out += ["", f"**✅ Pull requests merged ({len(data['prs_merged'])})**"]
    out += [f"- {link(p)} {t(p['title'])} — ``{at(p['author'])}``, merged {rel(p['merged_at'])}"
            for p in data["prs_merged"]] or ["- _None merged in this window._"]
    out += ["", "## 📊 Metrics", f"- 🆕 New issues total: {m['new_issues']}",
            f"- 🔧 In-progress items total: {m['in_progress']}",
            f"- 🚀 PRs opened total: {m['prs_opened']}",
            f"- 🗂️ PRs total (incl. drafts): {m['prs_total_incl_drafts']}",
            f"- ✅ PRs merged total: {m['prs_merged']}",
            f"- 🚨 Open blockers total: {len(old_blockers)}"]
    print("\n".join(out))
    sys.exit()

# ---- new layout ----
review_map = {"APPROVED": "approved", "CHANGES_REQUESTED": "changes requested",
              "REVIEW_REQUIRED": "review required"}
ci_map = {"passing": "✅", "failing": "❌", "pending": "⏳", "none": "–"}

# Needs a human today
needs = []
for p in data["open_prs"]:
    if not p["reviewers"] and p["review"] != "APPROVED" and p["age_days"] >= 3 and not p["draft"]:
        needs.append(f"- ⚠️ PR {link(p)} {t(p['title'])} — {p['age_days']}d old, no reviewer")
sec_un = [u for u in data["unassigned"] if set(u["labels"]) & {"security", "high", "bug"}]
for u in sec_un:
    needs.append(f"- 🙋 {link(u)} {t(u['title'])} — unassigned, {u['age_days']}d, {lbl(u['labels'])}")
for s in data["stale_issues"][:3]:
    needs.append(f"- 💤 {link(s)} {t(s['title'])} — idle {s['idle_days']}d")
needs = needs[:10]

# TL;DR
tl = []
if data["blockers"]:
    tl.append(f"{len(data['blockers'])} open blockers; oldest {link(data['blockers'][0])} ({data['blockers'][0]['age_days']}d).")
if sec_un:
    tl.append(f"{len(sec_un)} unassigned security/high/bug issues need an owner.")
noreview = [p for p in data["open_prs"] if not p["reviewers"] and not p["draft"] and p["review"] != "APPROVED"]
if noreview:
    tl.append(f"{len(noreview)} ready PRs have no reviewer assigned.")
if m["merged_last_7d"] or m["prs_merged"]:
    tl.append(f"{m['prs_merged']} PRs merged in window, {m['merged_last_7d']} in the last 7 days.")

out += ["## ☀️ Good morning, MLOps crew!", "", "### 🧭 TL;DR"]
out += [f"- {x}" for x in tl] or ["- Nothing urgent."]
if needs:
    out += ["", "### 🙋 Needs a human today"] + needs

out += ["", "## 📚 Activity digest"]
if data["new_issues"]:
    out += ["", f"**🆕 New issues ({len(data['new_issues'])})**"]
    out += [f"- {link(i)} {t(i['title'])} — {at(i['author'])}, labels: {lbl(i['labels'])}" for i in data["new_issues"]]
if data["in_progress"]:
    out += ["", f"**🔧 In-progress ({len(data['in_progress'])})**"]
    out += [f"- {link(i)} {t(i['title'])} — {at(i['assignees'][0]) if i['assignees'] else 'unassigned'}, "
            f"updated {rel(i['updated_at'])}" for i in data["in_progress"]]
if data["prs_opened"]:
    out += ["", f"**🚀 Pull requests opened ({len(data['prs_opened'])})**"]
    out += [f"- {link(p)} {t(p['title'])} — {at(p['author'])} ({'draft' if p['draft'] else 'ready'})" for p in data["prs_opened"]]
if data["prs_merged"]:
    out += ["", f"**✅ Pull requests merged ({len(data['prs_merged'])})**"]
    out += [f"- {link(p)} {t(p['title'])} — {at(p['author'])}, merged {rel(p['merged_at'])}" for p in data["prs_merged"]]
if data["workspace_requests"]:
    out += ["", f"**🏗️ Workspace requests ({len(data['workspace_requests'])})**"]
    for r in data["workspace_requests"]:
        prs = ", ".join(f"#{n}" for n in r["linked_prs"]) or "no PR yet"
        out.append(f"- {link(r)} {t(r['title'])} — {r['age_days']}d, {prs}")

out += ["", f"## 🔀 Open pull requests ({len(data['open_prs'])})"]
if data["open_prs"]:
    out += ["| # | Title | Author | Age | State | Review | CI | Reviewers |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for p in data["open_prs"]:
        rv = review_map.get(p["review"], "none")
        if not p["reviewers"] and rv in ("none", "review required") and p["age_days"] >= 3 and not p["draft"]:
            rv += " ⚠️"
        out.append(f"| {link(p)} | {t(p['title'])} | {at(p['author'])} | {p['age_days']}d | "
                   f"{'draft' if p['draft'] else 'ready'} | {rv} | {ci_map[p['ci']]} | "
                   f"{', '.join(at(r) for r in p['reviewers']) or 'none'} |")
else:
    out.append("_No open PRs._")

prev_sec = prev.split("Open blockers", 1)[1] if "Open blockers" in prev else ""
prev_nums = set(int(n) for n in re.findall(r"/issues/(\d+)", prev_sec.split("## 📊")[0])) if prev_sec else set()
out += ["", f"## 🚨 Open blockers ({len(data['blockers'])})"]
if data["blockers"]:
    out += ["| # | Title | Age | Labels | Assignee | Since last report |", "| --- | --- | --- | --- | --- | --- |"]
    for b in data["blockers"]:
        d = "" if not prev_nums else ("⏳ unchanged" if b["number"] in prev_nums else "🆕 new")
        out.append(f"| {link(b)} | {t(b['title'])} | {b['age_days']}d | {lbl(b['labels'])} | "
                   f"{', '.join(at(a) for a in b['assignees']) or 'unassigned'} | {d} |")
    cleared = sorted(prev_nums - {b["number"] for b in data["blockers"]})
    if cleared:
        out.append("")
        out.append("✔ Cleared since last report: " + ", ".join(f"#{n}" for n in cleared))
else:
    out.append("_No open blockers._")

out += ["", "## 📊 Metrics",
        f"- 🆕 New issues: {m['new_issues']} · 🔧 In progress: {m['in_progress']}",
        f"- 🚀 PRs opened: {m['prs_opened']} (incl. same-window merges: {m['prs_total_incl_drafts']}) · ✅ PRs merged: {m['prs_merged']}",
        f"- 🔀 Open PRs: {m['open_prs']} · median open-PR age: {m['median_open_pr_age_days']}d · merged last 7 days: {m['merged_last_7d']}",
        f"- 🚨 Open blockers: {m['open_blockers']}", "", header]
print("\n".join(out))
