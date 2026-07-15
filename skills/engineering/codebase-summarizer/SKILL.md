---
name: codebase-summarizer
description: Generate and maintain codebase summaries (CLAUDE.md / architecture docs) that orient future Claude sessions and human newcomers. Use this skill whenever the user asks to summarize, document, or explain a repo or package's structure, extract the coding conventions and best practices a codebase actually follows (and where the gaps are), create or improve a CLAUDE.md, or refresh/update an existing codebase summary that has gone stale. Trigger even if the user just says "help Claude understand this repo", "onboard me to this codebase", "is this doc still accurate", or points you at a repo and asks "what is this".
status: stable
---

# Codebase Summarizer

Produce summaries of a repo or package that make future Claude sessions immediately effective, and keep those summaries truthful as the code evolves. The primary reader is Claude; the secondary reader is a human newcomer. Both are served by the same thing: dense, concrete, verifiable statements — not marketing prose.

## The core principle: write claims, not vibes

Every sentence in a summary is a **claim** that a future session will rely on and that a future run of this skill must be able to **verify against the code**. This works only if claims are:

- **Located** — name the file, directory, or symbol: "Retry logic lives in `core/utils/retry.py` (`RetryPolicy`)", not "the package has robust retry handling".
- **Checkable** — a reader with the repo open can confirm or refute it in under a minute.
- **Load-bearing** — it changes what a reader would do. If deleting the sentence loses nothing, delete it.

Vague claims can never go stale because they never said anything; they also never helped anyone. Prefer a shorter summary of hard claims over a longer one of soft ones.

## Mode selection

First, look for an existing summary: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `ARCHITECTURE.md`, `docs/CODEBASE.md`, `.claude/` docs, or anything the user points at. Also check whether an existing `CLAUDE.md` contains a marker comment from a previous run (see Metadata block below).

- **Summary exists** → run **Update mode** (read `references/update-mode.md`). Do not regenerate from scratch; the existing doc may contain hand-written knowledge that a fresh scan cannot recover.
- **No summary** → run **Bootstrap mode** (below), which includes the conventions audit.
- **User asks only about conventions/best practices** → run just the conventions audit (read `references/conventions-audit.md`) and report findings; offer to fold them into a summary.

## Bootstrap mode

### 1. Survey before reading

Get the shape of the repo before reading any code in depth:

```bash
# Layout (adjust depth to repo size)
find . -type f -name "*.py" | head -50        # or the dominant language
tree -d -L 3 -I 'node_modules|__pycache__|.git|.venv|dist|build'
# Ground truth for entry points and structure
cat pyproject.toml setup.py package.json Cargo.toml 2>/dev/null
cat README.md 2>/dev/null
git log --oneline -15                          # what's been active lately
wc -l $(git ls-files '*.py') | sort -rn | head -20   # where the mass is
```

Identify: the package manifest (authoritative for name, deps, entry points, scripts), the top 3–5 largest/most-imported modules (these are the load-bearing walls), and the test layout.

### 2. Read the load-bearing code

Read the main entry points and the most-imported modules in full. Skim the rest at the level of module docstrings, class/function signatures, and `__init__.py` exports. You are building a mental model of: what problem this package solves, what the key abstractions are, how data flows through them, and what a contributor touches for a typical change.

### 3. Run the conventions audit

Read `references/conventions-audit.md` and follow it. The output feeds the "Conventions" and "Gaps" sections of the summary.

### 4. Choose placement

Recommend placement to the user based on the repo — state your recommendation and reasoning in one or two sentences, then proceed (or ask, if genuinely ambiguous):

| Repo shape | Placement |
|---|---|
| Small/medium single package, no CLAUDE.md or a trivial one | Everything in `CLAUDE.md` at repo root |
| CLAUDE.md exists with hand-written instructions (build commands, user preferences) | Separate `docs/ARCHITECTURE.md`; add one link line to CLAUDE.md. Never bury or rewrite a human's instructions |
| Monorepo / multiple packages / very large single package | Layered: root `CLAUDE.md` with the overview + a short per-package summary next to each package, linked from the root |

The test for "layered": would a single file exceed ~300 lines or force a session working on one package to wade through others? Claude context is precious — a session working in `packages/api` should be able to load only the root overview plus `packages/api`'s summary.

### 5. Write the summary

Read `references/summary-template.md` for the section structure and a worked example. Rules that matter most:

- Lead with a 2–4 sentence "what is this and why does it exist" a reader absorbs in ten seconds.
- The directory map explains **why** each area exists, not just what it's named. `services/ — one module per AWS service wrapper; add new service clients here` beats `services/ — service code`.
- Include the commands that actually work in *this* repo (test, lint, build, run), copied from CI config or Makefile — not guessed.
- Keep it honest about warts: if a module is deprecated, half-migrated, or known-confusing, say so. Future sessions waste the most time when docs describe the intended design instead of the actual one.
- End with the metadata block.

### 6. Metadata block

Close every generated summary (or generated section) with:

```markdown
<!-- codebase-summarizer: generated 2026-07-13, commit a1b2c3d, N claims -->
```

The commit is informational context (how old is this?), not the update mechanism — updates verify claims against code directly. The marker also tells a future run where machine-generated content begins, so it never mistakes human-written prose for its own output.

## Update mode

Read `references/update-mode.md` and follow it in full. The one-paragraph version: parse the existing summary into discrete claims; verify each against the current code (path exists? symbol exists? behavior still matches?); classify each as confirmed / stale / obsolete; then scan for significant *new* reality the summary doesn't mention (new top-level dirs, new key modules, new deps, changed commands). Edit surgically — fix what's wrong, add what's missing, and leave confirmed claims and all human-written content byte-identical. Report to the user what changed and why.

## Writing for the dual audience

Claude and a newcomer want the same document with one difference in emphasis: Claude never needs motivation or encouragement, and a newcomer never needs to be told things the file tree makes obvious. Write terse, declarative, path-anchored prose and both are served. Avoid: "This powerful library provides...", restating the directory tree without commentary, and documenting standard-library-level knowledge. Include: the non-obvious — the gotcha, the historical wart, the "you'd expect X but actually Y".

## Reference files

- `references/summary-template.md` — section structure, worked example, length calibration. Read before writing any summary.
- `references/conventions-audit.md` — how to extract conventions from code and identify gaps. Read for bootstrap step 3 or standalone audits.
- `references/update-mode.md` — the claim-verification workflow. Read whenever an existing summary is present.
