#!/usr/bin/env python3
"""Render a normalized transcript into a self-contained, theme-aware HTML page.

Usage:
    render.py <transcript.json> -o <page.html> [--summary summary.json] [--participant Ryan]

The page is written as artifact-ready body content: a <title>, a <style>, and markup.
It emits no <!doctype>, <html>, <head>, or <body> tags, loads nothing external, and
runs no JavaScript, so it satisfies a strict CSP.

`--summary` supplies the parts that need human/agent judgment (see summary.schema.json).
Without it the page still renders: masthead, stats, decision index, and full transcript.
"""
import json, html, re, os, sys, argparse, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md import render as md, _inline

MAX_RESULT = 5000
MAX_INPUT = 4000

E = lambda s: html.escape(s or "", quote=False)
EA = lambda s: html.escape(s or "", quote=True)

# harness chatter that is noise in a shared record
HIDE_PREFIXES = (
    "Base directory for this skill:",
    "<system-reminder>",
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<user-prompt-submit-hook>",
    "## Context Usage",
)

WRITE_TOOLS = {
    "Write": "wrote file",
    "Edit": "edited file",
    "NotebookEdit": "edited notebook",
}


def classify_user(text):
    """Split real human turns from slash commands, harness noise, and interrupts."""
    t = (text or "").strip()
    if t.startswith("[Request interrupted"):
        return "interrupt", t
    if "<command-name>" in t or "<command-message>" in t:
        name = re.search(r"<command-name>/?([^<]+)</command-name>", t)
        args = re.search(r"<command-args>(.*?)</command-args>", t, re.S)
        # a slash command carrying a substantial prompt IS the human's ask
        if args and len(args.group(1).strip()) > 80:
            return "human", args.group(1).strip()
        label = "/" + (name.group(1).strip() if name else "?")
        if args and args.group(1).strip():
            label += " " + args.group(1).strip()
        return "command", label
    for p in HIDE_PREFIXES:
        if t.startswith(p):
            return "meta", t
    return "human", t


def parse_ask(result):
    """Parse an AskUserQuestion result into (status, [(question, answer, notes)])."""
    r = (result or "").strip()
    if not r:
        return "no response", []
    if r.startswith("The user doesn't want to proceed"):
        said = re.search(r"the user said:\s*(.*?)(?:\n\s*Questions asked:|$)", r, re.S)
        note = re.sub(r"\s+", " ", said.group(1).strip()) if said else ""
        return "redirected", [("", note, "")]
    body = re.sub(r"\s*Read the answers carefully.*$", "", r, flags=re.S).strip()
    body = re.sub(r"^The user answered:\s*", "", body)
    marks = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r'"([^"]*)"=', body)]
    items = []
    for i, (s, e, q) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        ans = body[e:nxt].strip()
        notes = ""
        nm = re.search(r"\bnotes:\s*(.*)$", ans, re.S)
        if nm:
            notes, ans = nm.group(1).strip(), ans[: nm.start()].strip()
        items.append((q, ans, notes))
    return "answered", items or [("", body, "")]


def tool_summary(name, inp):
    inp = inp if isinstance(inp, dict) else {}
    n = name or "tool"
    short = n.split("__")[-1]
    if n == "Bash":
        return "Bash", (inp.get("command") or "").strip().split("\n")[0][:160]
    if n == "Read":
        return "Read", os.path.basename(inp.get("file_path", "")) or inp.get("file_path", "")
    if n in ("Write", "Edit", "NotebookEdit"):
        return short, os.path.basename(inp.get("file_path", ""))
    if n in ("Grep", "Glob"):
        return short, inp.get("pattern", "")
    if n in ("WebFetch", "WebSearch"):
        return short, inp.get("url") or inp.get("query", "")
    if n == "ToolSearch":
        return short, inp.get("query", "")
    if n == "Task" or n == "Agent":
        return short, inp.get("description", "")
    # MCP and anything else: show the most identifying scalar we can find
    for k in ("issueIdOrKey", "inwardIssue", "summary", "path", "query", "url", "projectKey", "name"):
        if inp.get(k):
            return short, str(inp[k])[:160]
    return short, ""


def fmt_ts(ts, tzoffset):
    if not ts:
        return None
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(datetime.timezone(datetime.timedelta(hours=tzoffset)))
    except Exception:
        return None


def build(data, summary, participant, tzoffset):
    events, meta = data["events"], data["meta"]
    S = summary or {}

    # ---- pass 1: counts -------------------------------------------------
    n_human = n_claude = 0
    tool_counts = {}
    decisions = []
    for ev in events:
        k = ev["kind"]
        if k == "user" and classify_user(ev["text"])[0] == "human":
            n_human += 1
        elif k == "assistant":
            n_claude += 1
        elif k == "tool":
            tool_counts[ev["name"]] = tool_counts.get(ev["name"], 0) + 1
            if ev["name"] == "AskUserQuestion":
                qs = (ev["input"] or {}).get("questions") or []
                decisions.append((qs[0].get("header") if qs else "") or "Decision")
    n_tools = sum(tool_counts.values())
    n_writes = sum(v for k, v in tool_counts.items() if k in WRITE_TOOLS)

    highlight = S.get("highlight_tools") or []
    n_highlight = sum(v for k, v in tool_counts.items() if k in highlight)

    start, end = fmt_ts(meta.get("first_ts"), tzoffset), fmt_ts(meta.get("last_ts"), tzoffset)
    hours = round((end - start).total_seconds() / 3600, 1) if start and end else 0

    # ---- pass 2: body ---------------------------------------------------
    parts, turn, dec, last_day = [], 0, 0, None
    for ev in events:
        ts = fmt_ts(ev["ts"], tzoffset)
        clock = ts.strftime("%-I:%M %p") if ts else ""
        day = ts.strftime("%A, %B %-d") if ts else None
        if day and day != last_day:
            parts.append(f'<div class="daybreak"><span>{E(day)}</span></div>')
            last_day = day

        k = ev["kind"]
        if k == "user":
            cls, text = classify_user(ev["text"])
            if cls == "meta":
                continue
            if cls == "interrupt":
                parts.append('<div class="marker"><span>interrupted by user</span></div>')
                continue
            if cls == "command":
                parts.append(f'<div class="marker cmd"><span><code>{E(text[:140])}</code></span></div>')
                continue
            turn += 1
            parts.append(
                f'<article class="entry human" id="t{turn}"><div class="rail">'
                f'<a class="tn" href="#t{turn}">{turn}</a><span class="clock">{E(clock)}</span>'
                f'<span class="who">{E(participant)}</span></div>'
                f'<div class="body prose">{md(text)}</div></article>'
            )

        elif k == "assistant":
            turn += 1
            parts.append(
                f'<article class="entry claude" id="t{turn}"><div class="rail">'
                f'<a class="tn" href="#t{turn}">{turn}</a><span class="clock">{E(clock)}</span>'
                f'<span class="who">Claude</span></div>'
                f'<div class="body prose">{md(ev["text"])}</div></article>'
            )

        elif k == "thinking":
            parts.append(
                '<div class="entry work"><div class="rail"></div><div class="body">'
                f'<details class="disc think"><summary><span class="tag">reasoning</span>'
                f'<span class="sum">{len(ev["text"].split())} words</span></summary>'
                f'<div class="prose dim">{md(ev["text"])}</div></details></div></div>'
            )

        elif k == "tool":
            name, inp = ev["name"], (ev["input"] if isinstance(ev["input"], dict) else {})

            if name == "AskUserQuestion":
                dec += 1
                qs = inp.get("questions") or []
                status, answers = parse_ask(ev["result"])
                hdr = (qs[0].get("header") if qs else "") or "Decision"
                blocks = []
                for q in qs:
                    opts = []
                    for o in q.get("options", []):
                        pv = f'<pre class="preview">{E(o.get("preview"))}</pre>' if o.get("preview") else ""
                        opts.append(
                            f'<li><span class="opt-label">{E(o.get("label",""))}</span>'
                            f'<span class="opt-desc">{_inline(o.get("description",""))}</span>{pv}</li>'
                        )
                    blocks.append(
                        f'<div class="q"><p class="q-text">{_inline(q.get("question",""))}</p>'
                        f'<ol class="opts">{"".join(opts)}</ol></div>'
                    )
                rows = "".join(
                    (f'<div class="ans-row">'
                     f'{f"<span class=chose>{E(a)}</span>" if a else ""}'
                     f'{f"<div class=notes><div class=prose>{md(nt)}</div></div>" if nt else ""}'
                     f"</div>")
                    for _, a, nt in answers
                )
                parts.append(
                    f'<article class="entry decision" id="d{dec}"><div class="rail">'
                    f'<a class="dn" href="#d{dec}">D{dec:02d}</a><span class="clock">{E(clock)}</span></div>'
                    f'<div class="body"><div class="dcard">'
                    f'<header class="dhead"><span class="dtopic">{E(hdr)}</span>'
                    f'<span class="dstatus">{E(status)}</span></header>{"".join(blocks)}'
                    f'<div class="answer"><span class="tag">{E(participant)}’s call</span>{rows}</div>'
                    f"</div></div></article>"
                )
                continue

            label, detail = tool_summary(name, inp)
            try:
                inp_s = json.dumps(inp, indent=1)
            except Exception:
                inp_s = str(inp)
            trunc_i, inp_s = len(inp_s) > MAX_INPUT, inp_s[:MAX_INPUT]
            res = ev.get("result") or ""
            trunc_r, res = len(res) > MAX_RESULT, res[:MAX_RESULT]
            badge = ""
            if name in highlight:
                badge = f'<span class="hl-badge">{E(S.get("highlight_label", "external write"))}</span>'
            parts.append(
                f'<div class="entry work"><div class="rail"></div><div class="body">'
                f'<details class="disc tool{" err" if ev.get("is_error") else ""}"><summary>'
                f'<span class="tag">{E(label)}</span><span class="sum mono">{E(detail)}</span>{badge}'
                f'</summary>'
                f'<div class="pane"><span class="pane-label">call</span>'
                f'<pre>{E(inp_s)}{"  … truncated" if trunc_i else ""}</pre></div>'
                + (f'<div class="pane"><span class="pane-label">result</span>'
                   f'<pre>{E(res)}{"  … truncated" if trunc_r else ""}</pre></div>' if res.strip() else "")
                + "</details></div></div>"
            )

    # ---- panels ---------------------------------------------------------
    outcomes = S.get("outcomes") or []
    connector = S.get("connector")
    oc = []
    for i, o in enumerate(outcomes):
        if i and connector:
            oc.append(f'<div class="arrow">│ {E(connector)}</div>')
        key = f'<span class="key">{E(o.get("key",""))}</span>' if o.get("key") else ""
        note = f'<span class="op">{E(o.get("note",""))}</span>' if o.get("note") else ""
        title = E(o.get("title", ""))
        if o.get("link"):
            title = f'<a href="{EA(o["link"])}" target="_blank" rel="noopener">{title}</a>'
        oc.append(f'<div class="tk">{key}<span class="ttl">{title}{note}</span></div>')
    outcome_panel = (
        f'<div><h2 class="sec">{E(S.get("outcome_heading", "What came out of it"))}</h2>'
        f'<div class="chain">{"".join(oc)}</div></div>'
        if oc else ""
    )

    stats = [
        (len(decisions), "decision points"),
        (n_tools, "tool calls"),
        (n_human, f"prompts from {participant}"),
    ]
    stats.append((n_highlight, S.get("highlight_stat", "external writes")) if highlight else (n_writes, "file writes"))
    stat_html = "".join(
        f'<div class="stat"><span class="n">{v}</span><span class="l">{E(l)}</span></div>' for v, l in stats
    )

    mx = max(tool_counts.values()) if tool_counts else 1
    tool_rows = "".join(
        f'<div class="trow"><span class="tname">{E(k.split("__")[-1])}</span>'
        f'<span class="tbar"><i style="width:{max(4, round(v / mx * 100))}%"></i></span>'
        f'<span class="tct">{v}</span></div>'
        for k, v in sorted(tool_counts.items(), key=lambda x: -x[1])
    )

    dec_index = "".join(
        f'<li><a href="#d{i+1}"><span class="dn-mini">D{i+1:02d}</span>{E(t)}</a></li>'
        for i, t in enumerate(decisions)
    )
    dec_section = (
        f'<section class="dindex"><h2 class="sec">'
        f'The {len(decisions)} questions Claude put to {E(participant)}</h2><ol>{dec_index}</ol></section>'
        if decisions else ""
    )

    span_txt = f'{start.strftime("%b %-d, %-I:%M %p")} → {end.strftime("%b %-d, %-I:%M %p")}' if start and end else ""
    title = S.get("title") or meta.get("title") or "Claude Code session"
    dek = S.get("dek") or ""
    cwd = (meta.get("cwd") or "").replace(os.path.expanduser("~"), "~")
    model = ", ".join(meta.get("models") or [])

    redacted = meta.get("thinking_redacted", 0)
    reasoning_note = (
        f" Claude’s internal reasoning is not reproduced here: the transcript stores "
        f"{redacted} reasoning blocks as signatures only, with no text."
        if redacted else ""
    )

    metabits = " ".join(
        f"<span>{x}</span>"
        for x in filter(None, [f"<b>{E(span_txt)}</b>", f"{hours} h elapsed" if hours else "", E(model), E(cwd)])
    )

    return f"""<title>{E(title)}</title>
<style>
{CSS}
</style>

<div class="wrap">

<header class="mast">
  <p class="eyebrow">{E(S.get("eyebrow", "Claude Code · session record"))}</p>
  <h1>{E(title)}</h1>
  {f'<p class="dek">{E(dek)}</p>' if dek else ''}
  <div class="mastmeta">{metabits}</div>
</header>

<section class="summary">
  {outcome_panel}
  <div>
    <h2 class="sec">Session at a glance</h2>
    <div class="stats">{stat_html}</div>
    <h2 class="sec">Tools used</h2>
    {tool_rows}
  </div>
</section>

{dec_section}

<section class="tsec">
  <h2 class="sec">Full record</h2>
  {"".join(parts)}
</section>

<p class="foot">Rendered from the local Claude Code transcript
(<code>{E(meta.get("session_id",""))}</code>). Tool calls are collapsed by default — expand any
row to see the exact call and its result; long payloads are truncated.{reasoning_note}</p>

</div>
"""


CSS = """
:root {
  --ground:#fcfcfd; --surface:#f3f4f7; --surface-2:#e9ebf1; --rule:#d7dbe4;
  --ink:#161e2b; --ink-2:#525c72; --ink-3:#8b94a8;
  --accent:#2c5a8a; --accent-soft:#e6edf6;
  --decision:#8a5a12; --decision-soft:#f7efe0;
  --hl:#2c6b59; --hl-soft:#e2efea;
  --danger:#98383a;
  --shadow:0 1px 2px rgba(20,30,50,.06), 0 8px 24px -16px rgba(20,30,50,.28);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,ui-serif,serif;
  --sans:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#111620; --surface:#181e29; --surface-2:#202836; --rule:#2d3644;
    --ink:#e3e7ef; --ink-2:#9ba5b9; --ink-3:#6c778d;
    --accent:#7bb0e0; --accent-soft:#1a2734;
    --decision:#d8a445; --decision-soft:#2a2317;
    --hl:#5fb69a; --hl-soft:#152722;
    --danger:#e08a84;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"] {
  --ground:#111620; --surface:#181e29; --surface-2:#202836; --rule:#2d3644;
  --ink:#e3e7ef; --ink-2:#9ba5b9; --ink-3:#6c778d;
  --accent:#7bb0e0; --accent-soft:#1a2734;
  --decision:#d8a445; --decision-soft:#2a2317;
  --hl:#5fb69a; --hl-soft:#152722;
  --danger:#e08a84;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7);
}

* { box-sizing:border-box; }
body {
  margin:0; background:var(--ground); color:var(--ink);
  font-family:var(--serif); font-size:17px; line-height:1.65;
  -webkit-font-smoothing:antialiased;
}
.wrap { max-width:1120px; margin:0 auto; padding:0 clamp(16px,4vw,40px) 96px; }

.mast { padding:clamp(40px,7vw,80px) 0 28px; border-bottom:2px solid var(--ink); }
.eyebrow { font-family:var(--sans); font-size:11px; font-weight:600; letter-spacing:.16em;
  text-transform:uppercase; color:var(--ink-3); margin:0 0 14px; }
h1 { font-size:clamp(30px,5.2vw,48px); line-height:1.1; margin:0 0 14px; font-weight:600;
  letter-spacing:-.015em; text-wrap:balance; }
.dek { font-size:clamp(17px,2.1vw,20px); color:var(--ink-2); margin:0; max-width:62ch; }
.mastmeta { display:flex; flex-wrap:wrap; gap:6px 22px; margin-top:22px;
  font-family:var(--sans); font-size:12.5px; color:var(--ink-3); }
.mastmeta b { color:var(--ink-2); font-weight:600; }

.summary { display:grid; grid-template-columns:1.35fr 1fr; gap:clamp(20px,3.5vw,44px);
  padding:36px 0 8px; align-items:start; }
@media (max-width:820px) { .summary { grid-template-columns:minmax(0,1fr); } }
h2.sec { font-family:var(--sans); font-size:11px; font-weight:700; letter-spacing:.16em;
  text-transform:uppercase; color:var(--ink-3); margin:0 0 16px; }
.chain { display:flex; flex-direction:column; gap:10px; }
.tk { display:grid; grid-template-columns:auto minmax(0,1fr); gap:14px; align-items:baseline;
  padding:13px 15px; background:var(--surface); border:1px solid var(--rule);
  border-radius:3px; border-left:3px solid var(--hl); }
.tk .key { font-family:var(--mono); font-size:13px; font-weight:600; color:var(--hl);
  white-space:nowrap; }
.tk .ttl { font-size:15.5px; line-height:1.45; }
.tk .ttl a { color:inherit; }
.tk .op { font-family:var(--sans); font-size:10.5px; text-transform:uppercase;
  letter-spacing:.1em; color:var(--ink-3); display:block; margin-top:3px; }
.chain .arrow { font-family:var(--mono); color:var(--ink-3); font-size:12px;
  padding-left:16px; letter-spacing:.1em; }
.stats { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1px;
  background:var(--rule); border:1px solid var(--rule); border-radius:3px;
  overflow:hidden; margin-bottom:26px; }
.stat { background:var(--ground); padding:14px 16px; }
.stat .n { font-family:var(--sans); font-size:24px; font-weight:650; letter-spacing:-.02em;
  font-variant-numeric:tabular-nums; display:block; }
.stat .l { font-family:var(--sans); font-size:10.5px; text-transform:uppercase;
  letter-spacing:.11em; color:var(--ink-3); }
.trow { display:grid; grid-template-columns:minmax(0,1fr) 84px 26px; gap:10px; align-items:center;
  font-family:var(--sans); font-size:12px; color:var(--ink-2); padding:3px 0; }
.tname { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tbar { background:var(--surface-2); height:5px; border-radius:3px; overflow:hidden; }
.tbar i { display:block; height:100%; background:var(--accent); opacity:.65; }
.tct { text-align:right; font-variant-numeric:tabular-nums; color:var(--ink-3); }

.dindex { margin:40px 0 8px; padding:24px 0 4px; border-top:1px solid var(--rule); }
.dindex ol { list-style:none; margin:0; padding:0; columns:2; column-gap:36px; }
@media (max-width:700px) { .dindex ol { columns:1; } }
.dindex li { break-inside:avoid; margin-bottom:5px; }
.dindex a { display:flex; gap:11px; align-items:baseline; text-decoration:none;
  color:var(--ink-2); font-family:var(--sans); font-size:13.5px; padding:4px 6px;
  border-radius:3px; }
.dindex a:hover { background:var(--decision-soft); color:var(--ink); }
.dindex a:focus-visible { outline:2px solid var(--accent); outline-offset:1px; }
.dn-mini { font-family:var(--mono); font-size:11px; color:var(--decision); font-weight:600; }

.tsec { margin-top:52px; border-top:2px solid var(--ink); padding-top:30px; }
.entry { display:grid; grid-template-columns:98px minmax(0,1fr); gap:22px;
  padding:4px 0; align-items:start; }
@media (max-width:760px) {
  .entry { grid-template-columns:minmax(0,1fr); gap:6px; }
  .rail { flex-direction:row!important; align-items:baseline!important; gap:10px!important;
          padding-top:10px!important; text-align:left!important; }
}
.rail { display:flex; flex-direction:column; gap:1px; padding-top:14px;
  font-family:var(--sans); font-size:11px; text-align:right; }
.tn { font-family:var(--mono); font-size:11px; color:var(--ink-3); text-decoration:none;
  font-variant-numeric:tabular-nums; }
.tn:hover { color:var(--accent); }
.clock { color:var(--ink-3); font-variant-numeric:tabular-nums; }
.who { font-weight:650; letter-spacing:.06em; text-transform:uppercase; font-size:10px;
  color:var(--ink-2); margin-top:2px; }
/* grid/flex children default to min-width:auto; wide code must scroll, not widen the page */
.body,.dcard,.q,.opts,.opts li,.answer,.disc,.pane,.notes { min-width:0; }

.entry.human .body { background:var(--accent-soft); border:1px solid var(--rule);
  border-left:3px solid var(--accent); border-radius:3px; padding:14px 20px; margin:8px 0; }
.entry.claude .body { padding:8px 0 12px; }
.entry.claude { border-bottom:1px solid var(--rule); }

.prose { overflow-wrap:break-word; }
.prose > *:first-child { margin-top:0; }
.prose > *:last-child { margin-bottom:0; }
.prose p { margin:0 0 .85em; max-width:68ch; }
.prose h3,.prose h4,.prose h5,.prose h6 { font-family:var(--sans); font-weight:650;
  margin:1.5em 0 .5em; line-height:1.3; text-wrap:balance; }
.prose h3 { font-size:19px; } .prose h4 { font-size:16px; }
.prose h5,.prose h6 { font-size:13px; text-transform:uppercase; letter-spacing:.09em;
  color:var(--ink-2); }
.prose ul,.prose ol { margin:0 0 .85em; padding-left:1.4em; max-width:68ch; }
.prose li { margin-bottom:.32em; }
.prose a { color:var(--accent); text-underline-offset:2px; }
.prose blockquote { margin:0 0 .85em; padding-left:16px; border-left:2px solid var(--rule);
  color:var(--ink-2); }
.prose hr { border:0; border-top:1px solid var(--rule); margin:1.6em 0; }
.prose code { font-family:var(--mono); font-size:.855em; background:var(--surface-2);
  padding:.12em .34em; border-radius:2px; }
.prose.dim { color:var(--ink-2); font-size:16px; }
.code-block { position:relative; margin:0 0 1em; background:var(--surface);
  border:1px solid var(--rule); border-radius:3px; overflow:hidden; }
.code-block pre { margin:0; padding:13px 15px; overflow-x:auto; }
.code-block code { background:none; padding:0; font-size:12.5px; line-height:1.55; }
.code-lang { position:absolute; top:0; right:0; font-family:var(--sans); font-size:9.5px;
  text-transform:uppercase; letter-spacing:.1em; color:var(--ink-3);
  background:var(--surface-2); padding:2px 8px; border-radius:0 0 0 3px; }
.tbl-wrap { overflow-x:auto; margin:0 0 1em; }
.prose table { border-collapse:collapse; font-family:var(--sans); font-size:13.5px; width:100%; }
.prose th,.prose td { border:1px solid var(--rule); padding:7px 11px; text-align:left;
  vertical-align:top; }
.prose th { background:var(--surface); font-weight:650; }

.daybreak { display:flex; align-items:center; gap:14px; margin:38px 0 20px;
  font-family:var(--sans); font-size:10.5px; font-weight:650; letter-spacing:.15em;
  text-transform:uppercase; color:var(--ink-3); }
.daybreak::before,.daybreak::after { content:""; height:1px; background:var(--rule); flex:1; }
.daybreak::before { max-width:98px; }
.marker { margin:9px 0 9px 120px; font-family:var(--sans); font-size:11px; color:var(--ink-3); }
@media (max-width:760px) { .marker { margin-left:0; } }
.marker code { font-family:var(--mono); font-size:11px; background:var(--surface-2);
  padding:2px 7px; border-radius:2px; color:var(--ink-2); }

.disc { border:1px solid var(--rule); border-radius:3px; background:var(--surface); margin:5px 0; }
.disc summary { display:flex; align-items:center; gap:10px; padding:7px 12px; cursor:pointer;
  list-style:none; font-family:var(--sans); font-size:12.5px; color:var(--ink-2);
  border-radius:3px; }
.disc summary::-webkit-details-marker { display:none; }
.disc summary::before { content:"\\203A"; font-family:var(--mono); color:var(--ink-3);
  transition:transform .15s ease; display:inline-block; font-size:15px; line-height:1; }
.disc[open] > summary::before { transform:rotate(90deg); }
.disc summary:hover { background:var(--surface-2); }
.disc summary:focus-visible { outline:2px solid var(--accent); outline-offset:1px; }
.tag { font-size:10px; font-weight:700; letter-spacing:.09em; text-transform:uppercase;
  color:var(--ink-3); white-space:nowrap; }
.disc.tool .tag { color:var(--accent); }
.disc.tool.err { border-color:var(--danger); }
.sum { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; flex:1; }
.sum.mono { font-family:var(--mono); font-size:11.5px; color:var(--ink-3); }
.hl-badge { font-family:var(--sans); font-size:9.5px; font-weight:700; text-transform:uppercase;
  letter-spacing:.09em; color:var(--hl); background:var(--hl-soft); padding:2px 8px;
  border-radius:10px; white-space:nowrap; }
.disc .prose { padding:4px 16px 14px; }
.pane { border-top:1px solid var(--rule); }
.pane-label { display:block; font-family:var(--sans); font-size:9.5px; font-weight:700;
  letter-spacing:.11em; text-transform:uppercase; color:var(--ink-3); padding:7px 14px 0; }
.pane pre { margin:0; padding:6px 14px 13px; overflow-x:auto; font-family:var(--mono);
  font-size:11.5px; line-height:1.5; color:var(--ink-2); }

.dn { font-family:var(--mono); font-size:12px; font-weight:700; color:var(--decision);
  text-decoration:none; }
.dcard { border:1px solid var(--rule); border-left:3px solid var(--decision);
  border-radius:3px; background:var(--ground); margin:10px 0; box-shadow:var(--shadow); }
.dhead { display:flex; align-items:center; justify-content:space-between; gap:12px;
  padding:10px 18px; background:var(--decision-soft); border-bottom:1px solid var(--rule); }
.dtopic { font-family:var(--sans); font-size:11px; font-weight:700; letter-spacing:.12em;
  text-transform:uppercase; color:var(--decision); }
.dstatus { font-family:var(--sans); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--ink-3); }
.q { padding:16px 18px 4px; }
.q-text { margin:0 0 12px; font-size:17px; line-height:1.5; max-width:66ch; }
.opts { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:9px; }
.opts li { border:1px solid var(--rule); border-radius:3px; padding:10px 13px;
  background:var(--surface); }
.opt-label { display:block; font-family:var(--sans); font-size:13px; font-weight:650;
  margin-bottom:3px; }
.opt-desc { display:block; font-size:14.5px; color:var(--ink-2); line-height:1.5; }
.preview { margin:9px 0 0; padding:10px 12px; background:var(--ground);
  border:1px solid var(--rule); border-radius:2px; font-family:var(--mono); font-size:11px;
  line-height:1.5; overflow-x:auto; color:var(--ink-2); }
.answer { padding:14px 18px 16px; border-top:1px solid var(--rule); margin-top:14px;
  background:var(--surface); }
.answer .tag { display:block; color:var(--decision); margin-bottom:6px; }
.ans-row { margin-bottom:8px; }
.chose { font-family:var(--sans); font-size:13px; font-weight:650; color:var(--ink); }
.notes { margin-top:4px; font-size:16px; }
.notes p { margin-bottom:.5em; }

.foot { margin-top:60px; padding-top:22px; border-top:1px solid var(--rule);
  font-family:var(--sans); font-size:12px; color:var(--ink-3); max-width:70ch; }
@media (prefers-reduced-motion:reduce) { * { transition:none!important; animation:none!important; } }
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--summary", help="JSON file supplying title, dek, and outcomes")
    ap.add_argument("--participant", default="You", help="display name for the human turns")
    ap.add_argument("--tz-offset", type=float, default=None,
                    help="hours from UTC for displayed times (default: this machine's offset)")
    a = ap.parse_args()

    data = json.load(open(a.transcript))
    summary = json.load(open(a.summary)) if a.summary else {}
    participant = summary.get("participant") or a.participant
    tz = a.tz_offset
    if tz is None:
        off = datetime.datetime.now().astimezone().utcoffset() or datetime.timedelta()
        tz = off.total_seconds() / 3600

    out = build(data, summary, participant, tz)
    with open(a.out, "w") as fh:
        fh.write(out)
    print(f"wrote {a.out}  {os.path.getsize(a.out)/1024:.0f}KB")


if __name__ == "__main__":
    main()
