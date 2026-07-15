# Skill authoring conventions

Source of truth for how skills in this repo are written.
The `new-skill` meta-skill walks through these steps; `audit-skills` and `bin/sync doctor` enforce them.

## Placement

Skills live in a domain tree under `skills/`: `skills/<domain>/[<subdomain>/]<skill-name>/SKILL.md`.
Nest by domain only, as deep as is natural for the topic (e.g. `skills/engineering/aws/ecs-debug/`).
Lifecycle is tracked in frontmatter (`status`), never in the directory structure.

The tree is flattened at sync time: each leaf directory containing a `SKILL.md` is symlinked as `~/.claude/skills/<skill-name>` and `~/.agents/skills/<skill-name>`.
Because of this, **directory names must be unique across the entire tree and all overlays**.

## Frontmatter

```yaml
---
name: ecs-debug              # required; must equal the directory name
description: Debug ECS ...   # required; phrased as a trigger: "Use when..."
status: stable               # stable | draft | deprecated; defaults to stable if omitted
---
```

- `description` is what an agent reads to decide whether to invoke the skill.
Write it as a trigger condition, not a summary of the body.
- `status: draft` skills are only synced with `bin/sync --include-drafts`.
- `status: deprecated` skills are never synced and get pruned from targets on the next sync.
Delete them after a decent interval; git remembers.

Additional keys that specific tools understand (e.g. `argument-hint`, `disable-model-invocation`) are allowed but optional.

## Vendored skills

Skills copied from external repos carry two extra frontmatter keys so updates stay reviewable:

```yaml
upstream: mattpocock/skills@skills/productivity/grill-me   # owner/repo@path-in-repo
upstream-commit: 697d4ce9742da5...                          # upstream commit last synced
```

The `sync-upstream` meta-skill checks these against the upstream repo, shows what changed, and applies approved updates while preserving local edits.
Local copies are yours: edit freely; upstream changes are merged deliberately, never auto-applied.

## Body

- Write tool-agnostic instructions: what to do, step by step, constraints, and failure modes.
Only reference a specific tool's features when the skill is inherently about that tool.
- Keep one skill to one job.
If the name needs "and", split it.
- Supporting files (scripts, templates) live next to `SKILL.md` inside the skill directory; the whole directory is symlinked, so relative references keep working.

## Markdown style

- Each full sentence on its own line.
- Plain dashes only; never em or en dashes.

## Lifecycle

1. New skills start as `status: draft`.
2. Test with `bin/sync --include-drafts`.
3. Promote to `stable` once proven; run `bin/sync`.
4. Retire by setting `deprecated` (sync prunes the live links), then delete later.
