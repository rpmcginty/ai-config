#!/usr/bin/env python3
"""List Claude Code session transcripts, newest first, optionally filtered.

Usage:
    find_session.py                 # all sessions
    find_session.py <search-term>   # match title, agent name, or first user message

Transcripts live at ~/.claude/projects/<slugified-cwd>/<session-id>.jsonl.
Titles are stored as `ai-title` / `agent-name` entries, usually near the top of the file.
"""
import json, os, sys, glob, argparse

ROOT = os.path.expanduser("~/.claude/projects")
SCAN_LINES = 400  # titles appear early; avoid reading multi-MB files in full


def session_rows(term=None, root=ROOT):
    rows = []
    for path in glob.glob(os.path.join(root, "*", "*.jsonl")):
        title = name = first_user = None
        try:
            with open(path, errors="replace") as fh:
                for n, line in enumerate(fh):
                    if n > SCAN_LINES and title:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    t = d.get("type")
                    if t == "ai-title":
                        title = d.get("title") or d.get("aiTitle")
                    elif t == "agent-name":
                        name = d.get("name") or d.get("agentName")
                    elif t == "user" and first_user is None:
                        c = d.get("message", {}).get("content")
                        if isinstance(c, str):
                            first_user = c[:200]
                        elif isinstance(c, list):
                            for b in c:
                                if isinstance(b, dict) and b.get("type") == "text":
                                    first_user = b.get("text", "")[:200]
                                    break
        except OSError:
            continue

        blob = " ".join(x for x in (title, name, first_user, path) if x).lower()
        if term and term.lower() not in blob:
            continue
        rows.append(
            {
                "mtime": os.path.getmtime(path),
                "path": path,
                "project": os.path.basename(os.path.dirname(path)),
                "id": os.path.basename(path)[:-6],
                "kb": os.path.getsize(path) / 1024,
                "title": title,
                "name": name,
                "first": first_user,
            }
        )
    rows.sort(key=lambda r: -r["mtime"])
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("term", nargs="?", help="case-insensitive substring to match")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    a = ap.parse_args()

    rows = session_rows(a.term)[: a.limit]
    if a.json:
        print(json.dumps(rows, indent=1))
        return
    if not rows:
        print("no matching sessions" + (f" for {a.term!r}" if a.term else ""))
        return
    for r in rows:
        print(f"{r['project']}")
        print(f"  id={r['id']}  {r['kb']:.0f}KB")
        print(f"  title={r['title']!r}")
        if r["first"]:
            print(f"  first={r['first'][:120]!r}")
        print(f"  path={r['path']}")
        print()
    print(f"{len(rows)} session(s)")


if __name__ == "__main__":
    main()
