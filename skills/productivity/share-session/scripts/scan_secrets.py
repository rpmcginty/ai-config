#!/usr/bin/env python3
"""Scan a transcript for credential-shaped strings before it leaves the machine.

Usage:
    scan_secrets.py <file> [<file>...]

Exits 1 if anything matches, so it works as a gate:
    python3 scan_secrets.py session.jsonl || echo "REVIEW BEFORE SHARING"

This is a tripwire, not a guarantee. It catches well-known token shapes; it cannot
recognize a bespoke internal secret. A human still reads the page before sharing.
"""
import json, re, sys, collections

PATTERNS = [
    ("aws_access_key",  re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws_secret",      re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*\S+")),
    ("github_token",    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("anthropic_key",   re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b")),
    ("openai_key",      re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("slack_token",     re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key",  re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("jwt",             re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("private_key",     re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("atlassian_token", re.compile(r"\bATATT[A-Za-z0-9_\-=]{20,}\b")),
    ("npm_token",       re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("bearer",          re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.]{24,}")),
    ("secret_assign",   re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|token)"
                                   r"\s*[=:]\s*[\"']?[^\s\"',}]{12,}")),
]


def walk(o, path, hits):
    if isinstance(o, str):
        for name, pat in PATTERNS:
            for m in pat.finditer(o):
                hits[name].append((path, m.group(0)[:140]))
    elif isinstance(o, dict):
        for k, v in o.items():
            walk(v, f"{path}.{k}", hits)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, f"{path}[{i}]", hits)


def scan(path):
    hits = collections.defaultdict(list)
    with open(path, errors="replace") as fh:
        head = fh.read(1)
        fh.seek(0)
        if head == "[" or head == "{":
            try:
                walk(json.load(fh), "", hits)
                return hits
            except Exception:
                fh.seek(0)
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                walk(json.loads(line), f"L{ln}", hits)
            except Exception:
                walk(line, f"L{ln}", hits)
    return hits


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    total = 0
    for path in sys.argv[1:]:
        hits = scan(path)
        if not hits:
            print(f"CLEAN  {path}")
            continue
        n = sum(len(v) for v in hits.values())
        total += n
        print(f"HITS   {path}  ({n})")
        for name, items in hits.items():
            seen = set()
            print(f"  == {name}: {len(items)}")
            for loc, val in items:
                if val in seen:
                    continue
                seen.add(val)
                print(f"     {loc}: {val}")
                if len(seen) >= 8:
                    print("     ...")
                    break
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
