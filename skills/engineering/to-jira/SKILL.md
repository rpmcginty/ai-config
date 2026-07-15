---
name: to-jira
description: Break a plan, spec, or the current conversation into tracer-bullet Jira issues with native blocking links. Use when the user wants to turn work into Jira tickets.
status: draft
disable-model-invocation: true
---

# To Jira

Break a plan, spec, or conversation into Jira issues that are tracer-bullet vertical slices, each declaring the issues that block it.
Adapted from `to-tickets` in mattpocock/skills; the slicing method is his, the publishing is Jira-native.

## Process

### 1. Gather context

Work from whatever is already in the conversation.
If the user passes a reference (a spec path, a Jira issue key or URL), fetch it and read its full body and comments.

### 2. Resolve the Jira destination

Establish before drafting, asking the user for whatever cannot be inferred:

- **Project key**: infer from an issue key in context if present, otherwise ask (listing visible projects if the tooling allows).
- **Parent**: an Epic or parent issue to attach the tickets to, if any.
- **Issue type**: default to Task; use the project's conventions if the user states them.
Check which types the project actually offers before creating.
- **Defaults**: labels, sprint, assignee, or components the user wants applied.

Use whatever Jira integration is available: Atlassian MCP tools (`createJiraIssue`, `createIssueLink`, `getVisibleJiraProjects`, `getJiraProjectIssueTypesMetadata`), a `jira`/`acli` CLI, or the REST API.
If none is available, stop and tell the user instead of writing tickets nowhere.

### 3. Explore the codebase (optional)

If you have not already explored the relevant code, do so.
Issue titles and descriptions should use the project's domain vocabulary.
Look for opportunities to prefactor: make the change easy, then make the easy change.

### 4. Draft vertical slices

- Each slice cuts a narrow but complete path through every layer (schema, API, UI, tests); vertical, not a horizontal slice of one layer.
- A completed slice is demoable or verifiable on its own.
- Each slice is sized to fit in a single fresh agent context window.
- Any prefactoring is its own ticket, done first.

Give each ticket its blocking edges: the other tickets that must complete before it can start.
A ticket with no blockers can start immediately.

Wide refactors (one mechanical change whose blast radius spans the codebase) are the exception to vertical slicing.
Sequence them as expand-contract: an expand ticket adds the new form beside the old; migrate tickets convert call sites in batches (per package or directory), each blocked by the expand; a contract ticket deletes the old form, blocked by every migrate batch.

### 5. Quiz the user

Present the breakdown as a numbered list showing, per ticket: title, blocked by, and what it delivers end to end.
Ask whether the granularity feels right, whether the blocking edges are genuine, and whether anything should merge or split.
Iterate until the user approves.

### 6. Publish to Jira

Create the issues in dependency order (blockers first) so links can reference real keys, then wire the edges:

1. Create each issue with the description template below, attaching the parent Epic and defaults from step 2.
2. Create a `Blocks` issue link from each blocker to the ticket it gates (so the ticket shows "is blocked by").
Confirm the link type name the instance offers; it varies.
3. Report the created keys as a list mirroring the approved breakdown, with links.

Do not close or modify any parent issue.

<issue-description-template>

## What to build

The end-to-end behaviour this ticket makes work, from the user's perspective, not layer-by-layer implementation.

## Acceptance criteria

- Criterion 1
- Criterion 2

## Blocked by

Issue keys of the tickets that gate this one, or "None, can start immediately".

</issue-description-template>

Avoid specific file paths or code snippets in descriptions; they go stale fast.
Exception: a prototype snippet that encodes a decision more precisely than prose (state machine, schema, type shape) can be inlined, trimmed to the decision-rich parts.

Work the frontier: any ticket whose blockers are all done, one ticket at a time, clearing context between tickets.
