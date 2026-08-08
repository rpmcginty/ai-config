#!/usr/bin/env python3
"""Audit vendored skills against their upstream repos.

For every SKILL.md carrying `upstream:` / `upstream-commit:` frontmatter, report:

  base      does the recorded upstream-commit still resolve? (a bogus or orphaned SHA
            silently breaks sync-upstream, whose compare step needs it as a merge base)
  behind    how many upstream commits have touched that path since the recorded one
  local     paragraphs that differ from the recorded base, ignoring reformatting

Divergence is measured semantically. This repo rewraps vendored bodies to sentence-per-line
and normalizes punctuation, so a raw line diff reports every vendored skill as changed and
is useless for spotting real overrides.

Usage: check-vendored.py [repo-root]      (defaults to $AI_CONFIG_HOME, else cwd)
Exit:  0 clean, 1 findings. Requires an authenticated `gh`.
"""
import base64
import difflib
import os
import pathlib
import re
import subprocess
import sys

# Substitutions this repo applies to vendored text; neutralized before comparing.
PUNCT = {"—": "-", "–": "-", "←": "<-", "→": "->",
         "“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."}


def gh_api(url, jq=None):
    cmd = ["gh", "api", url] + (["--jq", jq] if jq else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def frontmatter(text):
    """Return (dict, body). Only top-level scalar keys; enough for the tracking keys."""
    if not text.startswith("---"):
        return {}, text
    try:
        end = text.index("\n---", 3)
    except ValueError:
        return {}, text
    fm = {}
    for line in text[3:end].splitlines():
        if line[:1] not in (" ", "\t", "") and ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, text[end + 4:]


def paragraphs(body):
    """Body as normalized paragraphs: wrapping, whitespace, and punctuation neutralized."""
    for src, dst in PUNCT.items():
        body = body.replace(src, dst)
    out = []
    for para in re.split(r"\n\s*\n", body.strip()):
        para = re.sub(r"\s+", " ", para.strip())
        if para:
            out.append(para)
    return out


def audit(root):
    findings = 0
    rows = []
    for path in sorted(root.glob("skills/**/SKILL.md")):
        fm, body = frontmatter(path.read_text())
        upstream, sha = fm.get("upstream"), fm.get("upstream-commit")
        rel = str(path.relative_to(root))
        if not upstream:
            continue
        if not sha:
            rows.append((rel, "MISSING upstream-commit", "", ""))
            findings += 1
            continue
        if "@" not in upstream:
            rows.append((rel, f"MALFORMED upstream: {upstream}", "", ""))
            findings += 1
            continue

        repo, _, sub = upstream.partition("@")
        raw = gh_api(f"repos/{repo}/contents/{sub}/SKILL.md?ref={sha}", ".content")
        if raw is None:
            rows.append((rel, f"BASE UNRESOLVABLE @{sha[:8]}", "", f"{repo}@{sub}"))
            findings += 1
            continue

        hist = gh_api(f"repos/{repo}/commits?path={sub}&per_page=100", ".[].sha") or ""
        shas = hist.splitlines()
        behind = shas.index(sha) if sha in shas else None

        _, base_body = frontmatter(base64.b64decode(raw).decode("utf-8", "replace"))
        diff = [l for l in difflib.unified_diff(paragraphs(base_body), paragraphs(body),
                                                n=0, lineterm="")
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]

        behind_s = "up to date" if behind == 0 else (
            f"{behind} commit(s) behind" if behind is not None else "not in recent history")
        local_s = "verbatim" if not diff else f"{len(diff)} paragraph(s) overridden"
        if behind != 0:
            findings += 1
        rows.append((rel, "ok", behind_s, local_s))

    if not rows:
        print("no vendored skills found")
        return 0

    w = max(len(r[0]) for r in rows)
    for rel, status, behind, local in rows:
        if status != "ok":
            print(f"{rel:<{w}}  !! {status}  {local}")
        else:
            print(f"{rel:<{w}}  {behind:<22}  {local}")
    print(f"\n{findings} finding(s)" if findings else "\nall vendored skills clean")
    return 1 if findings else 0


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AI_CONFIG_HOME", ".")
    sys.exit(audit(pathlib.Path(arg).expanduser().resolve()))
