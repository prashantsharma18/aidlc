---
id: ctx-codebase-map
guide: ["2.8 A4", "4.10", "2.8 A7"]
---
# Standard: the codebase map

A short, curated document (context class 4) that records what the code cannot tell you: what
areas are for, which way dependencies point, who owns what, where changes go, and the traps.
It is neither a file listing nor generated documentation.

## Required sections
- What this service does (purpose, who calls it, what it calls)
- Areas: responsibility, owner, allowed dependencies
- Key flows: two or three, by file, with the invariant that must hold
- Where common changes go, each with the pattern to follow
- Shared capabilities to reuse (and how they behave on failure)
- Traps: fragile, generated, frozen or surprising areas
- Tests: how they run; what needs real dependencies

## Metadata line (exact format, checked)
`Owner: <team> · Last verified: YYYY-MM-DD, against commit <sha>`

## Building it
The agent drafts the structural skeleton read-only, each line labelled FACT or INFERENCE with a
file reference; a person supplies intent, ownership, the reasons for boundaries and the traps.
One or two screens; large areas get their own maps.

## Validation and freshness
- A fresh session with only the rules file and the map places three recent changes correctly
  and names what each would reuse.
- `aidlc check context-drift` fails if a named path does not exist, if the metadata line is
  missing, or if the commit is unknown; it warns when the date is older than the review interval.
- Update the map in the same PR as any structural change; when an agent works in the wrong place,
  ask whether the map would have prevented it.
