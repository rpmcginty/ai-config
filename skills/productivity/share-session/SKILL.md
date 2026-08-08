---
name: share-session
description: Render a past Claude Code session into a self-contained, shareable HTML page showing the back-and-forth, the decisions, and the tool work. Use when someone wants to show a teammate what happened in a session, share a working record of how a decision was reached, or publish a transcript as a readable document rather than a raw log.
status: stable
---

# Share a session

Turn a local Claude Code session transcript into a page a colleague can actually read: the human turns, Claude's replies, every tool call collapsed behind a disclosure, and the decision points pulled out as the spine.

## When something cheaper is enough

`/export [filename]` inside a live session writes the conversation to a file or the clipboard as plain text.
If the person just needs the gist, say so and stop; this skill is for when they want a document — structure, outcomes, and the reasoning trail — rather than a log dump.

There is no built-in share link for a teammate.
`/share` reports a conversation to Anthropic, and `/teleport` and `/remote-control` move a session between the same person's devices.
Neither one shares with a colleague.

## What you cannot recover

Check these before promising anything:

- **Reasoning text is usually gone.** Thinking blocks are typically stored signature-only, with the text stripped. `extract.py` reports the count as `thinking_redacted`. Never offer to show "Claude's reasoning" before confirming it survived.
- **Compacted sessions lose detail.** If the session was compacted, earlier turns exist only as the summary.
- **Sidechains are separate.** Subagent work appears as `isSidechain` entries; the scripts here render the main thread only.

## Steps

### 1. Find the session

```
python3 scripts/find_session.py <search-term>
```

Transcripts live at `~/.claude/projects/<slugified-cwd>/<session-id>.jsonl`.
Match on the `ai-title`, the agent name, or the first user message.
Confirm the match with the user before rendering — session titles repeat, and the wrong 2 MB transcript wastes everyone's time.

Do not `grep` these files.
JSONL lines here run to hundreds of kilobytes, and a context-capturing `grep -o` will hang.
Parse with Python.

### 2. Extract and profile

```
python3 scripts/extract.py <session.jsonl> -o transcript.json
```

This normalizes the stream, joins each `tool_result` back onto the `tool_use` that produced it, and prints a profile: time span, models, event counts, and the tool histogram.

Read the profile before designing anything.
It tells you what the session actually was — a debugging grind reads differently from a design interrogation, and the page should reflect which one you have.

### 3. Scan for secrets — do not skip this

```
python3 scripts/scan_secrets.py <session.jsonl>
```

Exits non-zero on a hit.
A transcript captures whatever passed through the session: file contents, command output, environment dumps, tokens pasted into a prompt.

The scanner is a tripwire for well-known token shapes, not a guarantee.
It cannot recognize a bespoke internal secret, an unreleased product name, or a customer's data.
Say plainly that you scanned, what it covers, and that the user should skim before sharing.
If it flags something, stop and show the user rather than redacting on your own judgment.

### 4. Write the summary

Copy `summary.example.json` and fill it in.
This is the judgment half of the job and the reason a person opens the page at all: what the session *produced*.

- `title` and `dek` — name the work and its outcome, not the activity. "Refining OCSDV-452 … ending with three linked stories" beats "a chat about tickets".
- `outcomes` — the artifacts that survived: tickets, PRs, files, decisions. Give each a `note` saying what changed. `connector` draws a relationship between them (`blocks`, `then`, `feeds`).
- `highlight_tools` — the tool names that mutated something outside the repo. These get a badge in the transcript and their own stat, so a reader can find the real writes among the reads.

Derive all of this from the transcript, never from memory.
Read the actual tool calls that mutated state and quote their inputs.

Omit the file entirely for a quick render; the page still produces masthead, stats, decision index, and full transcript.

### 5. Render

```
python3 scripts/render.py transcript.json -o page.html --summary summary.json --participant <name>
```

The page is artifact-ready body content: a `<title>`, one inline `<style>`, and markup.
No external loads, no JavaScript, both themes defined at token level.

`AskUserQuestion` calls become numbered decision cards showing the options offered and the answer given.
When a session used them, they are the most valuable thing on the page — they are the record of where judgment entered.

### 6. Check before publishing

```
python3 scripts/check.py page.html --browser --screenshot-dir shots/
```

Static checks catch the failure that actually ships: a color defined only inside a `@media` or `[data-theme]` block, which renders one theme's text on the other theme's ground.
The browser pass measures real layout and fails on horizontal page scroll.

Then look at the screenshots.
Automated checks confirm the page is well-formed, not that it is legible.

Two traps when reading a headless screenshot:

- Chrome enforces a minimum window width of roughly 485 px. Ask for 390 and you get a 390-px-wide capture of a 485-px-wide render, so content looks clipped when nothing is wrong. Trust `check.py --browser`, which measures `scrollWidth`, over your eyes.
- Wide `<pre>` content is *supposed* to run past the edge; it scrolls inside its own container. That is correct, not a bug.

### 7. Publish and hand it over

Publish the file as an artifact with a short `description` and an emoji `favicon`.

Tell the user two things: the page is **private until they share it** from the page's share menu, and where the source file lives if they want to re-render.

## Constraints

- Render only sessions belonging to the person asking.
A transcript is working material and can carry a third party's data.
- Never invent content that is not in the transcript. The summary interprets; it does not add.
- Long tool payloads are truncated (4 KB inputs, 5 KB results) and the page says so. Do not raise the caps to "be complete" — a 16 MB ceiling applies, and nobody reads a 40 KB JSON blob.
- Preserve what was actually said. Do not clean up the user's phrasing, silently drop turns where they were wrong, or reorder the exchange. The value of a record is that it is one.
