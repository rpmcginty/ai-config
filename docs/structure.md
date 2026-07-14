# Repo structure and sync mechanics

## Layout

```
ai-config/
├── AGENTS.md            # instructions for agents working on this repo
├── README.md            # overview and install
├── bin/
│   └── sync             # the only moving part; links everything into place
├── docs/
│   ├── conventions.md   # skill authoring rules
│   └── structure.md     # this file
├── instructions/        # global guidance, linked into $HOME
│   ├── AGENTS.md        # -> ~/AGENTS.md
│   ├── OPINIONS.md      # -> ~/OPINIONS.md
│   └── VOICE.md         # -> ~/VOICE.md
└── skills/              # hierarchical, tool-agnostic skill tree
    ├── engineering/
    ├── meta/            # skills that maintain this repo itself
    ├── productivity/
    └── writing/
```

## How sync works

`bin/sync` is idempotent and safe to run on every shell startup.

1. **Layers.** The layer list is this repo, followed by any overlay repos listed in `~/.config/ai-config/overlays` (one absolute path per line, `#` comments allowed).
Later layers win on name conflicts.
Overlays mirror this repo's shape (`skills/`, `instructions/`); this is how private work or personal content joins the public core without living in it.
2. **Skills.** Every leaf directory under a layer's `skills/` containing a `SKILL.md` is a skill.
`status: draft` and `status: deprecated` are skipped (see `docs/conventions.md`).
Each active skill is symlinked flat into `~/.claude/skills/<name>` and `~/.agents/skills/<name>`.
3. **Instructions.** Each file in `instructions/` is symlinked into `$HOME` (`~/AGENTS.md`, `~/VOICE.md`, `~/OPINIONS.md`).
If an overlay provides the same filename, the overlay's version wins.
4. **Pruning.** Symlinks in target dirs that point into a layer's `skills/` tree but no longer correspond to an active skill are removed.
Sync records every layer it has ever seen in `~/.config/ai-config/known-layers`, so links from a since-deregistered overlay are still pruned.
Links pointing anywhere else are never touched, so hand-installed or third-party skills are safe.
5. **Safety.** A regular file already sitting at a destination is never replaced without `--force`.

## Symlinks vs copies

Everything is symlinked, never copied: edits in the repo are live immediately, and `git pull` is the whole update story.
The exception this design leaves room for: if a future target needs *transformation* (e.g. generating Cursor rules, or merging layered instruction files into one), that becomes a render step inside `bin/sync`; nothing else changes.

Never symlink files the target tool itself rewrites (e.g. `~/.claude/settings.json`); those are out of scope for sync.

## Drift detection

`bin/sync doctor` reports without changing anything: missing or stale links, links pointing to the wrong place, regular files blocking destinations, frontmatter violations, and duplicate skill names.
It exits non-zero when issues are found, so it can gate CI or a pre-commit hook later.

## Shell integration and location discovery

The repo can live anywhere.
Every `bin/sync` run registers its own location in `~/.config/ai-config/home` and touches `~/.config/ai-config/last-sync`.
The `zsh-custom-scripts` plugin (`custom/default/400_ai-config.zshrc.zsh` there) resolves the repo via `$AI_CONFIG_HOME` if set, else the registered location, and on shell startup runs `bin/sync --quiet --pull` at most once per 24 hours based on the stamp.
`ai-config-sync` forces a run anytime and forwards arguments (`ai-config-sync doctor`).

With `--pull`, sync first fast-forwards every layer (this repo and overlays) from its remote, so machines converge on pushed changes within a day.
Pull guards: `--ff-only` (a diverged local branch is never merged), dirty worktrees are skipped with a warning, and git runs with batch-mode ssh plus a short connect timeout so an offline machine fails fast instead of hanging shell startup.

A fresh machine only needs: clone this repo anywhere, run `bin/sync` once to register it.
If the repo is moved, run `bin/sync` once from the new location; the stale registration heals itself.
