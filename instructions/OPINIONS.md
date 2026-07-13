# OPINIONS.md — Ryan's engineering viewpoints

Read this when a task would benefit from my perspective on how to build things.
These are defaults, not absolutes; a strong project-specific reason can override any of them.

## Architecture

- Prefer boring, well-understood tools over novel ones. Novelty is a cost that must be justified.
- Push complexity to the edges; keep the core small and easy to reason about.
- A little duplication is cheaper than the wrong abstraction. Wait for the third use before generalizing.
- Make illegal states unrepresentable. Prefer types and constraints over runtime checks and docs.

## Code

- Optimize for reading, not writing. The next person (or me in six months) is the audience.
- Functions do one thing. If the name needs "and", split it.
- Fail loud and early. No silent fallbacks that mask real problems.
- Delete dead code rather than commenting it out; git remembers.

## Testing

- Test behavior, not implementation. Tests that break on every refactor are a liability.
- One good end-to-end test beats ten brittle mocks-of-mocks unit tests.
- A flaky test is a broken test. Fix it or delete it, do not retry-loop it.

## Process

- Small, reviewable changes over big-bang PRs.
- Write the smallest thing that could possibly work, then harden it.
- If something is broken or a corner was cut, say so plainly. No overselling.
