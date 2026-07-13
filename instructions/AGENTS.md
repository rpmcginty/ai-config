# AGENTS.md

Common instructions for Ryan's AI coding agents across all scenarios.
Project-level `AGENTS.md` / `CLAUDE.md` files take precedence over anything here.

## General guidelines

- Never use the em dash "—" or en dash "–". Use a plain dash "-" instead.
- When writing commit messages, never auto-add your agent name as a co-author.
- Commit messages are plain imperative, lowercase fine: "fix get_version test", "update uv.lock".
No feat:/fix: prefixes unless the repo requires them.
- Never manually modify `CHANGELOG.md` files or any files marked as auto-generated.
- When writing or substantially editing long Markdown files, put each full sentence on its own line.
Preserve normal Markdown structure, but avoid wrapping multiple sentences onto one physical line.
- When making technical decisions, prefer long-term maintainability, robustness, and quality over implementation speed.
But simplicity beats speculative flexibility: do not add abstraction layers, config options, or generality that no current requirement demands.
- When fixing bugs, start by reproducing the bug in an end-to-end setting as closely aligned as possible with how an end user hits it.
This makes sure you find the real problem so your fix actually solves it.
If a true e2e repro is not feasible, reproduce as close to it as possible and note the gap.
- Hold a high standard for engineering excellence: linting, test failures, and test flakiness.
If you notice issues outside your current scope, fix them in a separate commit.
If the fix is non-trivial, flag it to Ryan instead of fixing it.

## Reference files

- When working on something that would benefit from Ryan's viewpoints, read `~/OPINIONS.md` to understand them.
- When writing prose posted under Ryan's identity (PR descriptions, Slack messages, review comments, docs), read `~/VOICE.md` first.
- Do not read `~/VOICE.md` for code, code comments, or commit messages.
Commit message style is defined above in this file.
