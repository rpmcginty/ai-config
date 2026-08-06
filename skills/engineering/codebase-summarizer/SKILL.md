---
name: codebase-summarizer
description: Generate and maintain codebase summaries (CLAUDE.md, ARCHITECTURE.md) that orient future sessions. Use when the user asks to summarize or document a repo's structure, onboard someone to a codebase, extract the conventions it actually follows, create or improve a CLAUDE.md, or check whether an existing summary has gone stale.
status: stable
---

# Codebase Summarizer

Produce summaries of a repo or package that make future Claude sessions immediately effective, and keep those summaries truthful as the code evolves.
The primary reader is Claude; the secondary reader is a human newcomer.
Both want the same document: dense, concrete, verifiable statements, not marketing prose.
Claude never needs motivation, and a newcomer never needs to be told what the file tree already shows.

## The core principle: write claims, not vibes

Every sentence in a summary is a **claim** that a future session will rely on and that a future run of this skill must be able to **verify against the code**.
This works only if claims are:

- **Located**: name the file, directory, or symbol.
"Retry logic lives in `core/utils/retry.py` (`RetryPolicy`)", not "the package has robust retry handling".
- **Checkable**: a reader with the repo open can confirm or refute it in under a minute.
- **Load-bearing**: it changes what a reader would do.
If deleting the sentence loses nothing, delete it.

Vague claims can never go stale because they never said anything; they also never helped anyone.
Prefer a shorter summary of hard claims over a longer one of soft ones.
The highest-value claims are the non-obvious ones: the gotcha, the historical wart, the "you would expect X but actually Y".

## Mode selection

First, look for an existing summary: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `ARCHITECTURE.md`, `docs/CODEBASE.md`, `.claude/` docs, or anything the user points at.

- **Summary exists**: read `references/update-mode.md` and follow it in full.
Do not regenerate from scratch; the existing doc may contain hand-written knowledge that a fresh scan cannot recover.
- **No summary**: run bootstrap mode, below.
- **User asks only about conventions or best practices**: read `references/conventions-audit.md`, follow it, report the findings, and offer to fold them into a summary.

## Bootstrap mode

### 1. Identify the stack

Determine the dominant language and find the package manifest before anything else.
The manifest is authoritative for the name, dependencies, entry points, and scripts.
Every later step is language-specific (which files hold the mass, which config encodes conventions, which commands are real), so settle this first instead of assuming.

### 2. Survey before reading

Get the shape of the repo before reading any code in depth.
Establish: the top-level layout, the three to five largest or most-imported modules (the load-bearing walls), the test layout, what the README claims this is, and what has been active in recent history.
How you gather that is yours to choose; suit it to the language and size of the repo.

### 3. Read the load-bearing code

Read the main entry points and the most-imported modules in full.
Skim the rest at the level of module docstrings, class and function signatures, and package exports.
You are building a mental model of what problem this package solves, what the key abstractions are, how data flows through them, and what a contributor touches for a typical change.

### 4. Run the conventions audit

Read `references/conventions-audit.md` and follow it.
Its output feeds the Conventions and Gotchas sections of the summary.

### 5. Choose placement

Recommend placement based on the repo.
State your recommendation and reasoning in one or two sentences, then proceed, or ask if it is genuinely ambiguous.

| Repo shape | Placement |
|---|---|
| Small/medium single package, no CLAUDE.md or a trivial one | Everything in `CLAUDE.md` at repo root |
| CLAUDE.md exists with hand-written instructions (build commands, user preferences) | Separate `docs/ARCHITECTURE.md`; add one link line to CLAUDE.md. Never bury or rewrite a human's instructions |
| Monorepo / multiple packages / very large single package | Layered: root `CLAUDE.md` with the overview + a short per-package summary next to each package, linked from the root |

The test for "layered": would a single file exceed ~300 lines, or force a session working on one package to wade through others?
Claude context is precious.
A session working in `packages/api` should be able to load only the root overview plus `packages/api`'s summary.

### 6. Write the summary

Read `references/summary-template.md` for the section structure, a worked example, and length calibration.
Write the result to the path chosen in step 5.
If a file already exists at that path, stop and switch to update mode; bootstrap never overwrites.

### 7. Verify your own claims, then stamp it

Walk your own output the way update mode would.
For each claim, name the file you read to get it.
Delete anything you cannot source, or rewrite it as something you can.

Then fence the generated content, opening and closing:

```markdown
<!-- codebase-summarizer: begin -->
...generated summary...
<!-- codebase-summarizer: end; generated 2026-07-30, commit a1b2c3d, N claims -->
```

Both fences are required.
They tell a future run exactly which lines are its own output, so it never edits human-written prose, and a single closing marker cannot do that once a human adds anything above the generated section.
The commit is informational context (how old is this?), not the update mechanism; updates verify claims against code directly.
