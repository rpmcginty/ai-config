---
name: new-skill
description: Scaffold a new skill in the ai-config repo with correct placement, naming, and frontmatter. Use when adding a skill to the skills/ tree or converting an ad-hoc prompt into a reusable skill.
status: stable
---

# new-skill

Scaffold a new skill in `~/workspace/ai-config` (or `$AI_CONFIG_HOME` if set).
Read `docs/conventions.md` in that repo first; it is the source of truth for authoring rules.

## Steps

1. Clarify what the skill should do and when an agent should reach for it.
If the trigger condition is fuzzy, sharpen it before writing anything.
2. Pick a location in the domain tree (`skills/engineering/`, `skills/writing/`, `skills/productivity/`, ...).
Nest by domain only, as deep as is natural.
Create a new domain directory if none fits; do not force a bad fit.
3. Pick a kebab-case name.
The directory name is the skill's identity and must be unique across the whole tree and any overlays, because sync flattens everything into one namespace.
Check with: `find skills -type d -name <name>` in each layer.
4. Create `skills/<domain-path>/<name>/SKILL.md` with frontmatter:
   - `name`: must equal the directory name
   - `description`: one or two sentences, phrased so an agent knows when to invoke it ("Use when...")
   - `status: draft`
5. Write the body: what to do, step by step, plus constraints and failure modes.
Keep it tool-agnostic; do not reference Claude-specific features unless the skill is inherently about them.
6. Run `bin/sync doctor` from the repo root and fix anything it reports.
7. Remind the user: drafts are not synced by default.
Test it with `bin/sync --include-drafts`, and flip `status` to `stable` once it has proven itself, then run `bin/sync`.
