---
name: audit-skills
description: Audit the ai-config repo's skills and instructions for convention violations, drift, and staleness. Use for periodic maintenance of the ai-config repo or when sync behaves unexpectedly.
status: stable
---

# audit-skills

Audit `~/workspace/ai-config` (or `$AI_CONFIG_HOME` if set) and report findings.
Do not fix anything without confirming with the user first, except trivially mechanical issues (e.g. a frontmatter name not matching its directory).

## Steps

1. Run `bin/sync doctor` from the repo root and include its output in the report.
It catches structural drift: missing or stale links, name mismatches, invalid statuses, duplicate names, blocked destinations.
2. Run `check-vendored.py` (next to this file) against the repo root to audit vendored skills.
It reports three things per skill: whether the recorded `upstream-commit` still resolves, how many upstream commits that path is behind, and how many paragraphs diverge from the recorded base.
   - `BASE UNRESOLVABLE` is the serious one: `sync-upstream` uses that commit as its merge base, so a bogus or orphaned SHA silently breaks updates for that skill.
   Find the real commit the local body matches and re-pin to it; do not just bump to upstream HEAD, which would claim changes you never took.
   - Divergence is measured on normalized paragraphs, so sentence-per-line rewrapping and punctuation substitution do not register.
   Anything it does report is a real local override — confirm it is still deliberate, and that upstream has not since moved in the same direction.
   - "N commits behind" is a prompt to consider `sync-upstream`, not a defect on its own.
3. Read every `SKILL.md` and judge what the script cannot:
   - Is the `description` phrased as a trigger ("Use when...") so an agent knows when to reach for it?
   - Does the body still match how the user actually works, or has it gone stale?
   - Do two skills overlap enough that they should merge, or is one skill doing two jobs and should split?
   - Is anything Claude-specific that could be written tool-agnostically?
4. Review lifecycle hygiene:
   - `status: draft` skills that have been around a while: propose promoting to `stable` or deleting.
   - `status: deprecated` skills: propose deleting once they have been deprecated for a while; git remembers.
5. Check `instructions/` files still reflect reality (referenced paths exist, guidance not contradicted by newer conventions).
6. Report findings grouped by severity: broken, drifted, judgement calls.
For each, propose a concrete fix.
Apply fixes only after the user agrees, then re-run `bin/sync doctor` to confirm clean.
