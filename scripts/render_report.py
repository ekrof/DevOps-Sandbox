#!/usr/bin/env python3
"""Deterministic emulation of the agent-written daily report (no LLM)."""
import json, re, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

data = json.load(open(sys.argv[1]))
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


def owners(i):
    return ", ".join(at(o) for o in i["owners"])


m = data["metrics"]
w = data["window"]
out = []
header = (f"_Last updated: {ts(data['generated_at'])} · "
          f"Report window: {ts(w['since'])} → {ts(w['until'])}_")

# ---- new layout ----
review_map = {"APPROVED": "approved", "CHANGES_REQUESTED": "changes requested",
              "REVIEW_REQUIRED": "review required"}
ci_map = {"passing": "✅", "failing": "❌", "pending": "⏳", "none": "–"}

# TL;DR
tl = []
if m["open_bugs"]:
    tl.append(f"{m['open_bugs']} open bugs.")
noreview = [p for p in data["open_prs"] if not p["reviewers"] and not p["draft"] and p["review"] != "APPROVED"]
if noreview:
    tl.append(f"{len(noreview)} ready PRs have no reviewer assigned.")
old = [p for p in data["open_prs"] if p["age_days"] >= 3 and not p["draft"]]
if old:
    tl.append(f"{len(old)} ready PRs open 3+ days.")
if m["merged_last_7d"] or m["prs_merged"]:
    tl.append(f"{m['prs_merged']} PRs merged in window, {m['merged_last_7d']} in the last 7 days.")

out += ["## ☀️ Good morning, MLOps crew!", "", "### 🧭 TL;DR"]
out += [f"- {x}" for x in tl] or ["- Nothing urgent."]

out += ["", "## 📚 Activity digest"]
if data["new_issues"]:
    out += ["", f"**🆕 New issues ({len(data['new_issues'])})**"]
    out += [f"- {link(i)} {t(i['title'])} — {owners(i)}, labels: {lbl(i['labels'])}" for i in data["new_issues"]]
if data["in_progress"]:
    out += ["", f"**🔧 In-progress ({len(data['in_progress'])})**"]
    out += [f"- {link(i)} {t(i['title'])} — {owners(i)}, "
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
                   f"{' '.join('`' + at(r) + '`' for r in p['reviewers']) or 'none'} |")
else:
    out.append("_No open PRs._")

news = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []
if news:
    out += ["", "## 📰 Azure ML news"]
    out += [f"- [{t(n['title'])}]({n['url']}) — {n['status']}" for n in news]

out += ["", "## 📊 Metrics",
        f"- 🆕 New issues: {m['new_issues']} · 🔧 In progress: {m['in_progress']}",
        f"- 🚀 PRs opened: {m['prs_opened']} (incl. same-window merges: {m['prs_total_incl_drafts']}) · ✅ PRs merged: {m['prs_merged']}",
        f"- 🔀 Open PRs: {m['open_prs']} · median open-PR age: {m['median_open_pr_age_days']}d · merged last 7 days: {m['merged_last_7d']}",
        f"- 🐞 Open bugs: {m['open_bugs']}", "", header]
print("\n".join(out))
