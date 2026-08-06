# Update mode

The claim-verification workflow for refreshing an existing summary.
Read whenever a summary already exists.

The governing rule: an existing summary may contain knowledge no scan can recover, written by a human who knew something the code does not show.
Never regenerate from scratch.
Verify, edit surgically, and preserve everything you did not disprove.

## 1. Separate generated from human content

Look for the marker comment:

```markdown
<!-- codebase-summarizer: generated 2026-07-13, commit a1b2c3d, N claims -->
```

- **Marker present** - everything from the start of the generated section to the marker is prior output of this skill, and is yours to edit. Anything outside it is human-written.
- **No marker** - treat the entire document as human-written. Verify it and propose changes, but do not rewrite it wholesale without saying so first.

Human-written content is never deleted, reworded, or reordered.
If a human sentence contradicts the code, flag it in your report and leave it in place; the human may be describing intent, a pending change, or a bug.

## 2. Parse the summary into claims

Walk the document and list every discrete assertion, with its line number.
A claim is anything a reader could act on: a path, a symbol, a command, a dependency, a stated convention, a description of behavior or flow.

Prose that asserts nothing checkable is its own finding.
Mark it **unverifiable** and either rewrite it into a located, checkable claim or delete it.
Do not leave it untouched just because it cannot be disproven.

## 3. Verify each claim against current code

Match the check to the claim type, cheapest first:

- Path claims: `test -e <path>`, or `ls` the parent to find where it moved.
- Symbol claims: `grep -rn "class Foo\|def foo" <dir>` - confirm it exists and still lives where the summary says.
- Import and dependency claims: read the manifest and lockfile, not the summary's memory of them.
- Command claims: confirm the command still appears in the Makefile, manifest scripts, or CI workflow. Run it only if it is cheap and safe; a test suite usually is not.
- Convention claims: re-check with the rule of three from `conventions-audit.md`, weighted toward recently changed files. A convention can decay without any file being deleted.
- Behavior and flow claims: read the code path. This is the expensive category, so batch it after the cheap checks have narrowed the field.

Do not verify a claim by finding the sentence that stated it somewhere else in the repo.
Verify against code.

## 4. Classify

- **Confirmed** - still true. Leave byte-identical, even if you would phrase it differently. Churn on confirmed lines makes the diff unreviewable and hides the real changes.
- **Stale** - right subject, wrong detail (moved path, renamed symbol, changed default, added parameter). Fix the detail, keep the sentence.
- **Obsolete** - the subject is gone. Delete the claim, and note the deletion in your report so the user can object.
- **Unverifiable** - too vague to check. Rewrite as a located claim if the underlying fact is real; otherwise delete.

## 5. Scan for new reality

A summary goes stale by omission as much as by error.
Use the commit in the marker as a starting point:

```bash
git diff --stat <marker-commit>..HEAD           # where the change landed
git log --oneline <marker-commit>..HEAD | head -30
git diff <marker-commit>..HEAD -- <manifest>    # new or dropped dependencies
```

Then check specifically for: new top-level directories, new modules large enough to be load-bearing, new or renamed commands in CI and the Makefile, removed subsystems, and conventions that changed direction.
If the marker commit is missing or unreachable, fall back to comparing the file tree and manifest against what the summary describes.

Add what a session would be misled by not knowing.
Not every new file deserves a line.

## 6. Edit surgically

Apply targeted edits to the specific stale lines.
Do not rewrite sections, reorder content, or reflow paragraphs that contain confirmed claims.
Match the existing document's voice and formatting, even where it differs from what you would have written.

Then update the metadata block with today's date, the current commit (`git rev-parse --short HEAD`), and the new claim count.

## 7. Report

Tell the user what changed and why, grouped by classification:

```markdown
Verified 24 claims in CLAUDE.md against commit e4f5a6b.

- Confirmed: 19
- Stale, fixed: 3
  - `clients/athena.py` moved to `query/athena.py` (line 34)
  - test command changed from `pytest` to `uv run pytest` per .github/workflows/ci.yml (line 12)
  - `Session.execute()` now takes a `timeout` argument (line 51)
- Obsolete, removed: 1
  - `clients/redshift.py` was deleted in 9a8b7c6 (was line 38)
- Added: 2
  - `query/cache/` (new, 400 lines, added 2026-06)
  - `pandas` is now a required dependency, not an extra
- Flagged, not changed: 1
  - Line 62 says schema regeneration is manual; `scripts/pull_schema.py` now runs in CI nightly. Human-written, so left in place.
```

Report the counts you actually verified.
If you skipped a category of check, say which and why.
