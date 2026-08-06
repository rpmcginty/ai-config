# Conventions audit

How to extract the conventions a codebase actually follows, and where they are declared but not honored.
Used by bootstrap step 3, or standalone when the user asks only about conventions and best practices.

The distinction that makes this useful: what the repo *declares* versus what the code *does*.
Report both, and every place they disagree.

## 1. Collect declared conventions

Read whatever encodes rules in this repo: editor and formatter config, the linter and type-checker settings (wherever this language keeps them), pre-commit hooks, `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`, any conventions doc, and the CI workflows.

CI is the strongest signal: a rule that gates merges is enforced, a rule in prose is aspirational.
Record for each declared rule whether it is enforced by tooling, checked in CI, or only written down.

## 2. Observe conventions in the code

Sample widely rather than reading deeply.
Take 8-15 files spread across different areas and different ages, including the most recently changed ones (`git log --name-only -30`).

Look for patterns in:

- Naming: module, class, function, test, and fixture naming; private prefix usage.
- Module layout: what lives at package root, how `__init__.py` or index files are used, whether public API is curated or incidental.
- Typing: annotation coverage, where types are defined, use of generics or protocols.
- Errors: a custom exception hierarchy or bare built-ins, where errors are wrapped, whether failures return or raise.
- Logging and output: logger acquisition pattern, structured versus free text, any `print` in library code.
- Configuration: env vars read inline versus a settings object, where defaults live.
- Dependencies: injected as arguments or imported as module globals.
- Tests: framework style, fixture placement, mocking approach, naming, and what is deliberately not tested.
- Docs: docstring style and whether it is consistent enough to be a rule.

## 3. Apply the rule of three

A pattern is a **convention** when it appears in at least three independent places and has no counterexample in recently changed code.
Two occurrences is a **tendency**; report it as such or not at all.
A pattern with counterexamples is a **split**, not a convention.

For splits, date both sides with `git log -1 --format=%ad -- <path>` on representative files.
The newer side is usually the intended direction; say which one new code should follow, and say why you concluded that.

## 4. Classify the gaps

Every finding lands in one of these buckets:

- **Unenforced** - declared in prose or config but violated in code, or enforced nowhere in CI. The most valuable gap to report, because contributors believe it is safe to rely on.
- **Undeclared** - followed consistently in code but written down nowhere. A new contributor or a fresh session will break it by accident. These belong in the summary's Conventions section.
- **Split** - two competing patterns, both live. Report both, name the winner, note the migration status if one exists.
- **Missing** - no convention where the codebase clearly needs one (no error strategy, no test layout, no config approach). Only claim this when the absence is causing visible inconsistency.

## 5. Report

Produce a table of conventions with evidence, then a list of gaps.

```markdown
| Convention | Evidence | Enforced by |
|---|---|---|
| Full type annotations on public functions | all of `src/`, spot-checked 12 files | `mypy --strict` in CI |
| Errors subclass `DatalakeError` | `errors.py` plus 6 raise sites | nothing |

Gaps:
- Unenforced: CONTRIBUTING.md requires docstrings on public functions; `query/` has them, `clients/` largely does not, and no linter checks it.
- Undeclared: tests are function-based pytest with no unittest classes anywhere, but nothing says so.
- Split: config is read via env vars in `config.py` and via `Settings` in newer modules. `Settings` is newer (added 2026-03) and is the direction to follow.
```

A convention you cannot point at is a guess, and a guessed convention in a summary is worse than a missing one, because future sessions will enforce it on the user's code.

State counts honestly: "spot-checked 12 of ~80 files" is a real claim, "the codebase consistently..." from a 12-file sample is not.
