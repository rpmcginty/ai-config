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
2. Read every `SKILL.md` and judge what the script cannot:
   - Is the `description` phrased as a trigger ("Use when...") so an agent knows when to reach for it?
   - Does the body still match how the user actually works, or has it gone stale?
   - Do two skills overlap enough that they should merge, or is one skill doing two jobs and should split?
   - Is anything Claude-specific that could be written tool-agnostically?
3. Review lifecycle hygiene:
   - `status: draft` skills that have been around a while: propose promoting to `stable` or deleting.
   - `status: deprecated` skills: propose deleting once they have been deprecated for a while; git remembers.
4. Check `instructions/` files still reflect reality (referenced paths exist, guidance not contradicted by newer conventions).
5. Report findings grouped by severity: broken, drifted, judgement calls.
For each, propose a concrete fix.
Apply fixes only after the user agrees, then re-run `bin/sync doctor` to confirm clean.
