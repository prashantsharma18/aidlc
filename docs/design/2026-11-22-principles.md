# Principles: five of pstack's principle skills, cited where they apply

Date: 2026-11-22 · Owner: framework owner (Prashant Sharma) · Status: approved by the framework owner in the session,
2026-11-22 (option B) · Research: `docs/research/2026-11-22-pstack-review/5-principles-mapping.md` (all 24 of
pstack's principles against aidlc today) and pstack's `skills/principle-*/SKILL.md` (`cursor/plugins`, folder
`pstack`, MIT, Lauren Tan).

## For the reviewer
- Who decides: the framework owner, in this design's review. No ADR: no gate, decision or stop changes.
- Tier and main risk: a framework change that adds five short skills and the lines that cite them. The main risk is
  a principle read on its own that seems to allow what an aidlc gate forbids, for example rewriting an existing test.
- What changed: five of pstack's principle skills, under pstack's names and in pstack's words, each with one
  "In aidlc:" note where a gate wins. Each is cited by name at the two or three steps where it applies, and the
  citing line carries the check itself, so it holds even when the principle file is not read.

## Why
pstack keeps 24 short principle skills and cites them by name where they apply. The mapping
(`5-principles-mapping.md`) checked all 24 against aidlc: 10 repeat a rule aidlc already holds, often as a gate; 6
only name a rule aidlc already has; 3 clash with aidlc's fixed decisions. Five add a check aidlc lacks:

| pstack principle | The check aidlc gains |
|---|---|
| `attack-the-premise` | When two fixes that share one premise fail the same way, write the premise down and test it |
| `fix-root-causes` | Fix where the system first went wrong; a guard is a fix only for a legitimate state; every same fault inside MAY CHANGE |
| `test-behavior-not-implementation` | A test fails when the behaviour breaks and still passes when only the internals change |
| `explain-the-number` | Before trusting a measured number, name what limits it and rule out that it measured something else |
| `exhaust-the-design-space` | For a decision with no precedent, compare two or three options by spike before recommending one |

aidlc's strength is its gates; these five add judgement the gates do not hold. The other 19 stay out: they would
repeat a gate, add only a name, or clash with one.

## Owner decisions (2026-11-22, in the session)
| Question | Decision |
|---|---|
| Which principles | Five (option B): the five above |
| Their names | pstack's titles without its `principle-` prefix (`attack-the-premise`, not `principle-attack-the-premise`), so they read like aidlc's other skills; the credit line keeps pstack's file name |
| Their words | pstack's own, kept word for word, with one "In aidlc:" note where a gate wins |
| An index of principles | None: the citations reach the AI at the step where each applies |
| Not now | The other 19 of pstack's principles |

## Part 1: The five principle skills
Each is a folder `skills/<name>/` with one `SKILL.md`, copied word for word from pstack, front matter
included, then two lines added at the end:

```text
**In aidlc:** <the gate that wins, in one sentence>
Adapted from pstack's `principle-<name>` (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan); its notice is in `skills/NOTICE`.

You draft; you never approve.
```

Its front matter gains `metadata: kind: principle`. Like pstack's, it keeps `disable-model-invocation: true`: the AI
never loads a principle by itself, and a person can still start one by name. Nothing loads one with a "Load the
`<name>` skill" line; a citing skill names it, and the file sits beside it at `../<name>/SKILL.md`.

| Principle | Its "In aidlc:" note |
|---|---|
| attack-the-premise | A second fix that fails the same way is a stop (`aidlc-build`'s Stop if): write the shared premise and the observation that tests it in the stop's report; testing the premise is diagnosis, not another attempt. |
| fix-root-causes | Every place inside MAY CHANGE; one outside it is a stop. The always-on signal is a proposal for its owner (`aidlc-feedback`). In production you propose only (`debugging-failures`). |
| test-behavior-not-implementation | It shapes the tests you write. An existing test that fails the two edits is a finding for its owner, never rewritten or deleted (`writing-tests`). |
| explain-the-number | aidlc has no `benchmark-checklist`: follow `tuning-performance`. A profiler that is not installed is a new dependency, which asks first. A measurement that turns out to measure something else is an assertion: changing it is `aidlc-build`'s Stop if. |
| exhaust-the-design-space | Each prototype is a spike (`playbook-spike.md`): outside the source, time-boxed, never committed. You recommend; the decider chooses. |

## Part 2: Where each is cited
Each citation is one sentence appended to an existing step. It carries the check in its own words and names the
principle in brackets, so the step holds alone and the AI can read the full principle when it needs the reason.

| Principle | Cited at (the step where its trigger happens) |
|---|---|
| attack-the-premise | `debugging-failures`, where the same failure returns after a different fix; `playbook-bug-fix` step 5 (before another attempt) |
| fix-root-causes | `debugging-failures` step 5 (fix the root cause); `playbook-bug-fix` step 5 (every instance inside MAY CHANGE) |
| test-behavior-not-implementation | `writing-tests`, the check "wrong code makes it fail"; `agents/reviewer-tests.md`, where it asks whether each test would fail on wrong code |
| explain-the-number | `tuning-performance`, "beat the noise, not just the mean"; `playbook-performance` step 3 |
| exhaust-the-design-space | `playbook-spike`, the variants step; `aidlc-design` step 3 (at least two real options) |

Ten citations in all. One sits in a word-limited stage (`aidlc-design`, 2,567 of 2,600). The others are in practices,
playbooks and an agent role, which have no limits.

## Part 3: The decision log names a principle that shaped a choice
When one of these principles shaped a judgement call, the decision-log row's *why* names it, for example
"… because the second fix failed the same way (`attack-the-premise`)". The row keeps its five fields
(`scripts/test_route_and_log.py` pins them). The compliance reviewer checks that a named principle fits the row. A
principle never turns a stop into a row.

## Kept, unchanged
- Every gate, decision and stop. Where a principle and a gate differ, the gate holds, and the "In aidlc:" note says so.
- "aidlc has four kinds of skill" stays true: the principle skills belong to the map, beside `using-aidlc`, and its
  four-kinds sentence names them there.
- No index or list of principles in `using-aidlc`.

## How it is tested
- **Structure tests:** each principle file matches pstack's word for word above its two added lines; its kind, its
  `disable-model-invocation`, its "In aidlc:" note and its credit; every citation sentence at its step; no "Load the"
  line names a principle; the decision-log wording and the compliance reviewer's check.
- **The validator:** a `kind: principle` skill keeps pstack's "Apply when" description and holds no gate sections;
  every other rule stays.
- **Existing tests:** the plan lists each one it must change for the owner's approval.

## Out of scope
- The other 19 of pstack's principles, and any index of principles.
- `bro`, `teach`, `ketchup` and pstack's tool skills (a later review).

## Risks
- **A principle read alone seems to allow what a gate forbids.** The "In aidlc:" note in each file, and every citation
  carries aidlc's bound in its own words.
- **pstack changes a principle later.** The files are copies with a credit line; a later plan may refresh them.

## The version
aidlc 8.3.0, a minor release: five new skills and the lines that cite them; no gate changes.
