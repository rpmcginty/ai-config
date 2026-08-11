---
name: codebase-quiz
description: Quiz an engineer on their understanding of a repo, narrowing from architecture down to implementation detail and hunting for confidently-held false beliefs. Use when someone wants to test or calibrate how well they actually know a codebase, check whether they understand an unfamiliar area well enough to change it safely, or find their blind spots in a repo they already work in.
status: draft
---

# codebase-quiz

Test how well someone actually understands a repo, and narrow in on what they believe confidently and wrongly.

This is a calibration instrument, not an exam.
The product of a session is not a score; it is the list of things the user is sure about and wrong about.
That list is the one thing they cannot get by asking a model to explain the repo, because they do not know to ask.

The user is quizzing themselves.
There is no integrity problem to defend against: looking up an answer defeats only their own purpose.
Never grade, rank, or congratulate.

## Hard rules

These are the difference between a useful session and one that actively miseducates.
Breaking any of them is worse than asking fewer questions.

**Cited.**
Never ask a question whose answer you have not read in a specific file during this session.
Every verdict names the `file:line` that proves it.
If you cannot cite it, you do not know it, and you must not test it.

**Consequential.**
A question is legitimate only if being wrong about it would cost something real: a broken PR, a wasted day, a bad design decision, an outage.
"What port does the dev server use" is cited and worthless.
Ask about the thing that would bite them.

**Real distractors.**
Wrong options must be drawn from something that is actually true elsewhere in the repo, or was true recently, or is what a reasonable person would assume.
Never invent a plausible-sounding fiction.
A good distractor is a real mechanism in the wrong place.

**Observable from here.**
When testing seams, test only what is visible from inside the scope: call sites, request and response shapes, schema and migration files, config, environment variables, timeout and retry behavior.
The internals of another repo are not citable, so they are not testable.

**Correctable.**
If the user pushes back on a verdict, re-open the cited file and re-derive the answer before responding.
If they are right, say so plainly, void the question, and record it as evidence of strength — they knew the repo better than your map of it.
Never defend a verdict you cannot re-source.

## Dimensions

Four, and only these four.

1. **Architecture and data flow** — what talks to what, where a request or record actually travels, which modules are load-bearing.
2. **Change navigation and blast radius** — where you would change X, and what breaks downstream when you do.
3. **Contracts and seams** — the APIs, schemas, events, and files by which this scope meets everything outside it.
4. **Failure modes and gotchas** — what breaks, how you would notice, what is fragile, and the "you would expect X but it is actually Y" landmines.

Conventions, idioms, and historical rationale are deliberately out of scope.

## Procedure

### 1. Survey wide

Read enough to see the shape of the repo, not enough to know it deeply.
The package manifest, the top-level layout, the test setup, what has been active in recent history, and any `CLAUDE.md` or `ARCHITECTURE.md` that exists.

Existing summaries orient you; they never grade.
Treat every claim in them as a lead to verify against code, never as an answer key.
A stale summary promoted into a question is how this skill teaches someone a falsehood about their own codebase.

### 2. Set scope and depth

Ask both in a single question round (in Claude Code, one `AskUserQuestion` call carrying two questions).
If the invocation already supplied a path or a depth, honor it and drop that question.

**Scope** — offer two to four concrete candidates derived from the shape you just surveyed:

| Repo shape | Candidates to offer |
|---|---|
| Single package | The whole repo, or one named subsystem within it |
| Monorepo | A specific package, a group of related packages, or the shared core layer |
| One service among many | This repo's internals, or this repo plus its seams to the outside |

Never offer a scope so wide that the ladder cannot reach implementation detail inside it.
A whole monorepo is not a scope.

**Depth** — quick (about 6 questions), standard (about 12), or deep (about 20).

### 3. Gate

Try to build four cited, consequential tier-1 questions, one per dimension.
If you cannot, stop and say so plainly.
A repo that is mostly generated code, mostly configuration, or too thin to have an architecture has nothing worth quizzing anyone on, and twelve questions about YAML keys is worse than an honest no.

### 4. Tier 1: diagnose

Exactly four questions, one per dimension, asked together in one batch.
This is the diagnostic that makes everything after it possible, so it never shrinks, whatever the depth.

Each question offers three real answer options plus a fourth: *"Not sure — I'd have to look it up."*
That fourth option is mandatory on every question in the session.
It makes honesty free and separates not knowing from being wrong, which is the entire signal.

### 5. Verdicts

Immediately after each batch, give every question a verdict: right or wrong, the correct answer in one or two sentences, and the `file:line`.
Keep it short.
The citation matters more than the explanation, because the citation is what lets the user check you.

Then classify each answer:

- **Confidently wrong** — they picked a real option and it was wrong. The highest-value finding in the session.
- **Confidently right** — they picked the correct option. Unverified: it may be real knowledge or a lucky surface.
- **Unknown** — they picked "not sure". Already resolved; there is nothing more to learn here.

### 6. Descend

Pick the next tier's branch by priority:

1. A **confidently wrong** answer, if there is one. Drill it to show exactly where the belief breaks.
2. Otherwise a **confidently right** answer. Drill it to find out whether it survives depth or was surface-deep.
3. Never an **unknown**. They already told you they do not know; those go straight to the reading list.

Read deep into that branch now.
This is the point where you spend real effort on code, not before.

Each tier is one branch, narrower and more specific than the last, batched in one call like tier 1.
Depth sets the ladder:

| Depth | Tiers |
|---|---|
| Quick | 4 + 2 |
| Standard | 4 + 4 + 4 |
| Deep | 4 + 5 + 5 + 6 |

By the final tier the questions should be about specific lines, specific ordering, specific edge cases: the kind of thing only someone who has read the file knows.

### 7. Blank slate: stop early

If tier 1 comes back mostly "not sure" — three of four, or two with the other two wrong — abandon the ladder.
The finding is already established at question four: they have not read this repo yet.
Say so without judgement, deliver the reading list, and offer a guided tour of the scope instead.
A quiz is the wrong instrument for a blank slate.

### 8. Debrief

Always debrief, including when the user stops partway.
Three lists, in this order:

1. **Confidently wrong** — read these first, because they are currently operating on a false belief. Each with its `file:line`.
2. **Verified solid** — what survived depth. Say it plainly so they stop second-guessing it.
3. **Blind spots they flagged** — the "not sure" answers, which are honest gaps rather than errors.

Then a reading list: concrete `file:line` targets in priority order, drawn from the citations the session already produced.
Every gap must resolve to something they can read in the next twenty minutes.

## Failure modes

- **Trivia.** If a question could be answered from the file tree or the README, it is not a question. Delete it.
- **Uncited confidence.** If you are writing a verdict without having had the file open, stop and go read the file.
- **Piling on.** Descending into an area the user already admitted they do not know teaches nothing and reads as cruelty.
- **Scope too wide.** If the last tier's questions still sound like tier-1 questions, the scope was never narrow enough to descend into.
- **Grading.** No scores, no percentages, no "good job". The three lists are the output.
- **Capability-sensitive.** Drawing a real distractor from neighboring code is the hardest thing this skill does.
If questions keep coming out as trivia despite the rules above, the model or effort level is too low for this.
Say so and stop, rather than continuing to produce cheap questions.
