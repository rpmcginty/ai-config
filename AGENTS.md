# Working on this repo

This repo holds Ryan's portable AI agent configuration: a hierarchical skill tree, global instruction files, and the sync script that links them into live locations.
Global ground rules in `instructions/AGENTS.md` apply here too (notably: sentence-per-line markdown, no em or en dashes, plain lowercase imperative commits).

## Map

- `skills/`: domain tree of `SKILL.md` skills; flattened by sync, so leaf directory names are globally unique. Lifecycle is `status:` frontmatter (`stable` | `draft` | `deprecated`), never directory placement.
- `instructions/`: files linked into `$HOME`; edits are live immediately on every machine that cloned this repo.
- `bin/sync`: idempotent linker; runs on shell startup, so keep it fast and never let it prompt.
- `docs/conventions.md`: skill authoring rules. `docs/structure.md`: sync mechanics.

## Rules

- Adding or changing a skill: follow `docs/conventions.md`, then run `bin/sync doctor` and fix what it reports.
- New skills start as `status: draft`; do not create them `stable`.
- Never rename a skill directory casually: the name is the skill's public identity in every tool's namespace.
- `bin/sync` must stay idempotent and must never touch symlinks it does not own (links pointing outside the layers' `skills/` trees).
- Do not add content here that belongs in a private overlay: employer-specific names, internal URLs, anything sensitive.
This repo is intended to be public.
