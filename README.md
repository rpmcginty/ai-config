# ai-config

Portable AI agent configuration: skills, instructions, and voice, written tool-agnostically and synced into whatever agent harness is on the machine.
Optimized for Claude Code today; designed so other tools are an extra sync target, not a rewrite.

## What lives here

- **`skills/`**: a hierarchical, domain-organized tree of [Agent Skills](https://agentskills.io) (`SKILL.md` directories).
The hierarchy is for humans; sync flattens it into the flat namespaces tools expect.
- **`instructions/`**: global guidance linked into `$HOME`: `AGENTS.md` (agent ground rules), `VOICE.md` (how I write), `OPINIONS.md` (engineering viewpoints).
- **`bin/sync`**: the only moving part.
Symlinks everything into place, prunes what no longer exists, and diagnoses drift with `bin/sync doctor`.
- **`docs/`**: [structure and sync mechanics](docs/structure.md), [skill authoring conventions](docs/conventions.md).
- **`skills/meta/`**: skills that maintain this repo itself (`new-skill` scaffolder, `audit-skills` reviewer).

## Install

```sh
git clone <this repo> anywhere/you/like
anywhere/you/like/bin/sync
```

That links active skills into `~/.claude/skills/` and `~/.agents/skills/`, and instruction files into `$HOME`.
Symlinks mean edits here are live immediately and `git pull` is the whole update story.

The repo's location is not special: the first `bin/sync` run registers it in `~/.config/ai-config/home`, and everything else finds it from there (set `AI_CONFIG_HOME` to override).
With the [zsh-custom-scripts](https://github.com/rpmcginty/zsh-custom-scripts) plugin installed, sync also runs quietly on shell startup, throttled to once per 24 hours.

## Everyday commands

```sh
bin/sync                    # link + prune everything
bin/sync doctor             # report drift and convention violations, change nothing
bin/sync --include-drafts   # also link status: draft skills, for testing
bin/sync --force            # replace regular files sitting where links belong
bin/sync --pull             # fast-forward this repo and overlays from their remotes first
```

The zsh startup hook uses `--pull`, so each machine picks up edits pushed from other machines within a day without any manual step.
Pulls are safe by construction: fast-forward only, skipped when the worktree is dirty, and never allowed to prompt (offline machines fail fast and quiet).

## Adding a skill

Use the `new-skill` skill from any agent, or by hand: create `skills/<domain>/<name>/SKILL.md` per [docs/conventions.md](docs/conventions.md), start it as `status: draft`, promote to `stable` once proven.
Skill lifecycle lives in frontmatter, not directory structure.

## Private overlays

This repo is the public core.
Machine- or employer-specific content lives in separate private repos with the same shape (`skills/`, `instructions/`), registered in `~/.config/ai-config/overlays` (one path per line).
Sync layers them on top: overlay skills join the same namespace, and on a name conflict the later layer wins.
See [docs/structure.md](docs/structure.md) for details.

## Maintenance

Run the `audit-skills` skill periodically; it wraps `bin/sync doctor` plus judgement checks (stale drafts, overlapping skills, descriptions that no longer trigger well).
`bin/sync doctor` exits non-zero on issues, so it can gate CI later if this repo grows into one.
