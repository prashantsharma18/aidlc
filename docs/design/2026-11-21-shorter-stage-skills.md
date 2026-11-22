# Shorter stage skills: per-case steps in references

Date: 2026-11-21 · Owner: framework owner (Prashant Sharma) · Status: approved by the framework owner in the session,
2026-11-21 · Change list: item D3 (shorter stage skills). No ADR: no decision or gate changes.

## For the reviewer
- Who decides: the framework owner, in this design's review.
- Tier and main risk: a framework change to how five stage skills are laid out. The main risk is an AI that skips a
  reference and misses a route's steps. Every stop and every decision stays in `SKILL.md`, so a missed reference
  cannot skip a gate.
- What changed: the five biggest stage skills keep their main path and all their gates in `SKILL.md`, and move the
  how-to steps for each route or case into `references/<case>.md`, read on a named condition. Text moves word for
  word; a rule that another file owns becomes a pointer. No decision, no stop and no behaviour changes.

## Why
The stage skills have grown: `aidlc-build` and `aidlc-plan` are each about 4,100 words, `aidlc-start` about 3,100,
`aidlc-design` about 2,700 and `aidlc-specify` about 2,050. Most of it is on long lines, so a skill of 200 lines is
about 5,000 tokens, and most of every skill is a route or a case the work in hand does not take (route G, F0 and D1
briefs, route S, several repositories, revisions, amendments).

Two costs follow. The AI reads every case on every run, which makes the main path harder to follow. And the same rule
is written in several places: in Plans 24 and 25 most review findings were one rule worded differently in two files.

The open Agent Skills format has the place for this already: a `references/` folder a skill reads only when it needs
it. aidlc uses it today (`aidlc-onboard/references/suppression-rules.md` and four practice skills), and the validator
checks that every named `references/…` file exists.

## Owner decisions (2026-11-21, in the session)
| Question | Decision |
|---|---|
| The tests | Each test file's `skill(name)` helper reads `SKILL.md` and the skill's `references/*.md`; no assertion changes; new tests and validator checks keep the gates in `SKILL.md` |
| Scope | The five biggest stages: `aidlc-build`, `aidlc-plan`, `aidlc-start`, `aidlc-design`, `aidlc-specify` |
| The split | Per skill, by case: each skill's own `references/` files, one per case it handles |
| The version | 7.2.0 |

## What stays and what moves
| Stays in `SKILL.md` | Moves to `references/<case>.md` |
|---|---|
| The front matter, When to use, Inputs, the main path's Steps, Produces | The how-to steps for one route or case: what to write, in which order, from which template |
| Gate, Stop if, Common excuses, Red flags and Rules, whole | Examples and details only that case needs |
| Every stop condition and every decision, route-specific ones too, each at least as a one-line entry in Stop if or in the Gate | |

### The three rules
1. **A reference never holds a gate.** It has no Gate, Stop if, Common excuses, Red flags or Rules section. When a
   step in a reference can stop the work or needs a person's decision, that stop or decision is in `SKILL.md`, and
   the reference points to it ("stop as this skill's Stop if says").
2. **`SKILL.md` names every reference with the condition to read it**, at the step where the case begins: "On route
   D1 or F0 (brief mode): read `references/brief-mode.md` now and follow it; then go on with step 6." Each reference
   opens with one line: which step of which skill sends you here, and that the skill's Gate, Stop if and Rules still
   apply.
3. **A rule is written once.** A reference states the steps of its case. A rule that another file owns (the tiers
   file's decisions table, the decision log's row, route S's limits in `aidlc-start`) is a pointer to that file, never
   a restatement.

A step that every route takes stays in `SKILL.md`. A sentence that applies to two cases lives in the main path, or in
one reference that the other points to; it is never copied.

## The proposed split
The plan fixes the exact cut from the text; this is the shape.

| Skill (words today) | `references/` files | `SKILL.md` target |
|---|---|---|
| `aidlc-plan` (4,100) | `brief-mode.md` (F0 and D1 briefs), `several-repositories.md` (parts, the coordination plan), `route-g.md` (slice 0), `revision.md` (re-plans) | under 2,500 words |
| `aidlc-build` (4,150) | `route-s.md` (the standard class, the recipe pause), `route-g.md` (the slice 0 skeleton), `several-repositories.md` (parts), `stacked-slices.md` | under 2,500 words |
| `aidlc-start` (3,100) | `route-s.md` (reading the Standard changes list), `several-repositories.md` (the workspace, parts), `route-g.md` | under 2,500 words; the route-change table stays in `SKILL.md`, because it says when a person decides |
| `aidlc-design` (2,700) | `several-repositories.md` (contracts, cross-repository ADRs), `route-g.md` (`new-system.md`), `amendment.md` | under 2,000 words |
| `aidlc-specify` (2,050) | `amendment.md` | under 1,800 words |

No text is deleted. It moves word for word, except where rule 3 turns a restated rule into a pointer; the plan lists
each such pointer.

## How it is tested
- **The test helpers (owner's choice).** In each of the ten test files that define `skill(name)`, the helper reads
  `SKILL.md` and then the skill's `references/*.md` in name order. No assertion changes: every sentence a test pins
  is still found in the skill's folder. Each changed helper is one item for the owner's approval in the plan.
- **The validator** (`scripts/validate.py`, aidlc's own contributor check; it does not ship to teams, ADR 0024): a
  stage skill's reference has no `## Gate`, `## Stop if`, `## Common excuses`, `## Red flags` or `## Rules` heading;
  every file in a stage skill's `references/` is named in its `SKILL.md`; every named file exists (as today).
- **New tests:** the five `SKILL.md` files meet their word targets; each reference opens with its "sent here from
  step N" line; the five skills keep their sections, their byte-identical Gate line and "You draft; you never
  approve."; in a reference, every sentence that tells the AI to stop points to the skill's Stop if ("as this
  skill's Stop if says"), and the per-task reviews check that each such stop is listed there.
- **Behaviour:** no new eval case. The existing route cases (`route-d1-build`, the F0 and route S cases,
  `gate-tier2-design-plan-once`, the lane cases) check that the AI reads the reference and follows it, when they run;
  none has run yet (no API key).

## What changes in aidlc
| New | Changed |
|---|---|
| `references/` files in the five skills | The five `SKILL.md` files: the moved steps become a named condition and a pointer |
| The validator's two checks, and their tests | The `skill(name)` helper in ten test files (owner items) |
| | `AGENTS.md` Standards: a stage skill may keep per-case steps in `references/`, under the three rules |
| | The change list: D3 covered; `.claude-plugin/plugin.json` 7.2.0 |

aidlc still ships no code and needs no code-host feature (ADR 0024).

## Kept, unchanged
- Every decision in the tiers file's decisions table, and every stop (ADR 0026, ADR 0027).
- Tests first; never editing an existing assertion; the AI never approves or merges (ADR 0023).
- The stage skills' sections, Gate lines and "You draft; you never approve."; the load table in
  `scripts/test_loads.py` (a "Load the `<name>` skill" phrase stays where it is).

## Out of scope
- The smaller stages (`aidlc-intent`, `aidlc-discover`, `aidlc-verify`, `aidlc-review`, `aidlc-release`,
  `aidlc-operate`, `aidlc-feedback`, `aidlc-onboard`) and the `parallel-lanes` workflow skill.
- D1 (one autonomous lane), B3, H1 and H3; Copilot and Codex adapters (parked).

## Risks
- **The AI skips a reference.** The condition sits at the step where the case begins, and every stop stays in
  `SKILL.md`, so a skipped reference cannot skip a gate; the route evals show it when they run.
- **Text is lost in the move.** The pinned sentences are checked across the folder, and the plan's dry run compares
  the old and new text, so only the listed pointers differ.
- **A rule drifts between a skill and its reference.** Rule 3, the validator's checks and the per-task reviews guard
  against it.
- **A pinned sentence ends up in the wrong file.** The helper now finds it anywhere in the folder; the new test that
  a reference's stop sentences point to Stop if, the reviews check each is listed there, and the gate sections'
  tests keep the gates where they must be.

## The version
aidlc 7.2.0, a minor release: no decision or stop changes, but the skills' layout does, and an AI that fails to read a
reference would behave differently.
