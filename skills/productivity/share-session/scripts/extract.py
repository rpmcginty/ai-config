#!/usr/bin/env python3
"""Normalize a Claude Code session transcript (JSONL) into an ordered event list.

Usage:
    extract.py <session.jsonl> -o <transcript.json>

Output shape:
    {"meta": {...}, "events": [{"kind": "user"|"assistant"|"thinking"|"tool", ...}]}

Notes:
  - Tool results arrive as `tool_result` blocks on the FOLLOWING user entry; they are
    joined back onto their originating `tool_use` here, and those carrier entries dropped.
  - `thinking` blocks are usually stored signature-only with empty text. Empty ones are
    dropped, and `meta.thinking_redacted` records how many were seen.
"""
import json, os, argparse, collections


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def extract(path):
    raw = []
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                raw.append(json.loads(line))
            except Exception:
                continue

    # tool results live on later user entries, keyed by tool_use_id
    results = {}
    for d in raw:
        if d.get("type") != "user":
            continue
        c = d.get("message", {}).get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = b

    meta = {
        "source": os.path.abspath(path),
        "session_id": os.path.basename(path)[:-6],
        "first_ts": None,
        "last_ts": None,
        "title": None,
        "cwd": None,
        "version": None,
        "models": [],
        "thinking_redacted": 0,
    }
    models = collections.Counter()
    events = []

    for d in raw:
        t = d.get("type")
        ts = d.get("timestamp")
        if ts:
            if meta["first_ts"] is None:
                meta["first_ts"] = ts
            meta["last_ts"] = ts
        if t == "ai-title" and not meta["title"]:
            meta["title"] = d.get("title") or d.get("aiTitle")
        if d.get("cwd") and not meta["cwd"]:
            meta["cwd"] = d["cwd"]
        if d.get("version") and not meta["version"]:
            meta["version"] = d["version"]
        msg = d.get("message") or {}
        if msg.get("model"):
            models[msg["model"]] += 1

        if t == "user":
            c = msg.get("content")
            # drop pure tool_result carriers; their payload is merged into the tool event
            if isinstance(c, list) and c and all(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in c
            ):
                continue
            body = text_of(c)
            if not body.strip():
                continue
            events.append({
                "kind": "user",
                "ts": ts,
                "origin": (d.get("origin") or {}).get("kind"),
                "source": d.get("promptSource"),
                "text": body,
            })

        elif t == "assistant":
            c = msg.get("content")
            if not isinstance(c, list):
                c = [{"type": "text", "text": text_of(c)}]
            for b in c:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text" and b.get("text", "").strip():
                    events.append({"kind": "assistant", "ts": ts, "text": b["text"]})
                elif bt == "thinking":
                    th = (b.get("thinking") or b.get("text") or "").strip()
                    if th:
                        events.append({"kind": "thinking", "ts": ts, "text": th})
                    else:
                        meta["thinking_redacted"] += 1
                elif bt == "tool_use":
                    res = results.get(b.get("id"))
                    res_text, is_err = "", False
                    if res:
                        is_err = bool(res.get("is_error"))
                        rc = res.get("content")
                        if isinstance(rc, str):
                            res_text = rc
                        elif isinstance(rc, list):
                            chunks = []
                            for rb in rc:
                                if isinstance(rb, dict):
                                    if rb.get("type") == "text":
                                        chunks.append(rb.get("text", ""))
                                    elif rb.get("type") == "image":
                                        chunks.append("[image]")
                            res_text = "\n".join(chunks)
                    events.append({
                        "kind": "tool",
                        "ts": ts,
                        "name": b.get("name"),
                        "input": b.get("input"),
                        "result": res_text,
                        "is_error": is_err,
                    })

    meta["models"] = [m for m, _ in models.most_common()]
    return {"meta": meta, "events": events}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jsonl")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()

    data = extract(a.jsonl)
    with open(a.out, "w") as fh:
        json.dump(data, fh, indent=1)

    kinds = collections.Counter(e["kind"] for e in data["events"])
    tools = collections.Counter(e["name"] for e in data["events"] if e["kind"] == "tool")
    m = data["meta"]
    print(f"wrote {a.out}")
    print(f"  title:   {m['title']!r}")
    print(f"  span:    {m['first_ts']} -> {m['last_ts']}")
    print(f"  models:  {', '.join(m['models']) or 'n/a'}")
    print(f"  events:  {dict(kinds)}")
    if m["thinking_redacted"]:
        print(f"  note:    {m['thinking_redacted']} reasoning blocks stored signature-only (no text)")
    print(f"  tools:   {dict(tools.most_common(12))}")


if __name__ == "__main__":
    main()
