---
name: sync-upstream
description: Check vendored skills for upstream changes and apply them deliberately. Use when the user wants to pull updates for skills copied from other repos, or to vendor a new skill from an external repo.
status: stable
---

# sync-upstream

Vendored skills are copies from external repos, tracked via two frontmatter keys:

```yaml
upstream: mattpocock/skills@skills/productivity/grill-me   # owner/repo@path-in-repo
upstream-commit: 697d4ce9742da5...                          # upstream commit last synced
```

Updates are deliberate and reviewed, never blind overwrites: local copies may carry intentional edits (at minimum `status:` and these tracking keys, which upstream does not have).

## Checking for updates

Run from the ai-config repo root (and each overlay that vendors skills).

1. Find vendored skills: `grep -rl '^upstream:' skills`.
2. For each, parse `owner/repo` and `path` from the `upstream:` key and read `upstream-commit`.
3. Get the latest upstream commit touching that path:
   `gh api "repos/<owner/repo>/commits?path=<path>&per_page=1" --jq '.[0].sha'`
   If it equals `upstream-commit`, the skill is up to date; report and move on.
4. Otherwise fetch what changed upstream since the recorded commit:
   `gh api "repos/<owner/repo>/compare/<upstream-commit>...<latest>" --jq '.files[] | select(.filename | startswith("<path>")) | {filename, status, patch}'`
5. Show the user each skill's upstream diff and ask which to take.
6. For approved updates, apply the upstream changes to the local files:
   - Preserve local frontmatter keys (`status`, `upstream`, `upstream-commit`) and any deliberate local edits to the body; where an upstream change conflicts with a local edit, show the conflict and let the user decide.
   - Ignore upstream files the local copy deliberately omits (e.g. `agents/` harness metadata) unless the body references them.
7. Set `upstream-commit` to the latest sha, run `bin/sync doctor`, and commit with a message like `sync grill-me from upstream`.

## Vendoring a new skill

1. Copy the skill directory from the upstream repo into the domain tree (SKILL.md plus any files the body references; skip unrelated harness metadata).
2. Ensure frontmatter `name` matches the local directory name and add `status: draft`.
3. Add the `upstream:` key and set `upstream-commit` to the latest commit touching that path (command in step 3 above).
4. Follow the normal lifecycle from `docs/conventions.md` (doctor, test via `--include-drafts`, promote).
