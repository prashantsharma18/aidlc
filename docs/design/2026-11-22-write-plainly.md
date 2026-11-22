# Write plainly: five writing and explaining practices from pstack

Date: 2026-11-22 · Owner: framework owner (Prashant Sharma) · Status: approved by the framework owner in the session,
2026-11-22 · Research: `docs/research/2026-11-22-pstack-review/` (report 3, section 1; report 4, how pstack calls
these skills) and pstack's `unslop`, `technical-writing`, `in-your-own-words`, `how` and `why` (`cursor/plugins`,
folder `pstack`, MIT, Lauren Tan).

## For the reviewer
- Who decides: the framework owner, in this design's review. No ADR: no gate, decision or stop changes.
- Tier and main risk: a framework change that adds five practice skills and the lines that call them. The main risks
  are two skills whose descriptions read alike, so the AI loads the wrong one, and a writing pass that rewrites code,
  commands or quoted text.
- What changed: five new practice skills, adapted from pstack, each its own folder with pstack's name. Other skills
  call the base one, `unslop`, as pstack does: a standing rule in the entry workflows, a last-pass line in every skill
  that writes prose, and a load at the moments a person decides. No stage's text is rewritten.

## Why
Every stage writes for a person: a spec the product owner approves, a pull request description the code owner reads,
a stop message, a commit body. aidlc says "write short sentences" in its own rules, but no skill says how, and nothing
checks a draft for the habits that make AI text slow to read. pstack has these as small skills that its main skill and
other skills call (report 4): `unslop` is applied to every reply and named by seven other skills, `technical-writing`
to every document, pull request description and commit message. aidlc also has no skill for the two questions a
person asks most often about code they did not write: how does this work, and why is it like this.

## Owner decisions (2026-11-22, in the session)
| Question | Decision |
|---|---|
| One skill or several | Separate skills, as pstack has them |
| Which ones, and their names | Five, keeping pstack's names: `unslop`, `technical-writing`, `in-your-own-words`, `how`, `why` |
| Not now | `bro`, `teach`, `ketchup` |
| How `unslop` is reached | As pstack does: a standing rule, a last-pass line in the skills that write prose, and loads at the moments a person decides |
| `aidlc-onboard` | Nothing new depends on it: the owner is not sure it stays, which is a separate discussion |
| pstack's tool and principle skills | A separate, later review against the aidlc skills they overlap |

## Part 1: The five practices
Each keeps its pstack name (owner, 2026-11-22), so its source and its credit are plain from the name. aidlc's other
practices keep their doing-word names, and `docs/codebase-map.md` gains the rule "a practice adapted from pstack keeps
pstack's name". Each is a practice skill (`metadata.kind: practice`) with the practice sections (When to use, Steps,
Checks, Stop if, Common excuses, Red flags, Rules). None has `disable-model-invocation`, because a stage loads them
(`scripts/test_loads.py` requires a loaded skill to be loadable by the model); a person can also start each one by
name. Each credits pstack, and `skills/NOTICE` lists them.

| aidlc practice (pstack's name) | What it adapts | What it does | Called by |
|---|---|---|---|
| `unslop` | pstack's `unslop` | The last pass on any text a person reads. A numbered catalog of AI tells (filler, hedges, AI vocabulary, dashes used as connectors, bold labels that restate their line, generic closers, praise openers, abstract metaphor nouns), each with its plain fix. The rule numbers are stable ids other skills cite; a removed rule leaves a gap. It calls no other skill | the standing rule; `technical-writing`; `writing-documentation`; `committing-changes`; `reviewing-code`; the investigation playbook; a person |
| `technical-writing` | pstack's `technical-writing` (its sentence layers) | How the sentences of a document, a pull request description or a commit body read: name the reader and what they decide; the plain word; one idea per sentence; the condition before the step; one name per thing; no sentence open to two readings; a pull request description a reviewer reads in under a minute, that links logs instead of pasting them. Its last step applies `unslop` | the stages, at the moments a person decides (Part 3); a person |
| `in-your-own-words` | pstack's `in-your-own-words` | Before work starts on a request, restate in your own words the person's goal and the problem they are solving, and ask them to correct it | `aidlc-intent` and `stress-testing-decisions` (as pstack's `interrogate` calls it); a person |
| `how` | pstack's `how` | Answers "how does X work" and "where should this live": state the reading of the question, brief the `explorer` agent with it (read-only, every finding cited), and present its answer as a mental model a senior engineer new to the area can work from | `aidlc-discover`; a person |
| `why` | pstack's `why` | Answers "why is it like this" from the record, not the code: the commits and pull requests that introduced the target and each later change (`git log`, `git blame`, the review tool where it can be read), the authors' own words cited, inferences marked as inferences, and what the record does not answer | `aidlc-discover`; the bug-fix playbook's USE SKILLS; a person |

pstack's Diátaxis section (one document, one mode: tutorial, how-to, reference, explanation) is about which kind of
document to write, so it goes into `writing-documentation`'s first step, not into `technical-writing`. pstack's
repository specifics (tabs in code snippets, its own tools) are left out.

## Part 2: How the other skills reach `unslop`
pstack reaches `unslop` three ways (report 4). aidlc does the same:

| Pattern | pstack | aidlc |
|---|---|---|
| A standing rule in what every session runs | `poteto-mode`: "Prose, your reply included → **unslop**" | One rule in `story-run` and in `lane-run`'s `references/worker.md`, split as pstack splits it: every reply a person reads goes through `unslop`; every document, pull request description and commit body goes through `technical-writing`, which applies `unslop` as its last pass. `starter/repo/AGENTS.md` may carry the same line for a team that copies it |
| A last-pass line in every skill that writes prose | `technical-writing`, `teach`, `recall`, `blast-radius`, `show-me-your-work` | `technical-writing`, `writing-documentation`, `committing-changes` (commit bodies and pull request text) and `reviewing-code` (findings a person reads): "apply `unslop` as the last pass" |
| A playbook step | investigation: "Apply the **unslop** skill to the reply" | The investigation playbook has no bundle (`aidlc-discover` reads it), so its finding step names the skill: "write the finding through `unslop`". The bug-fix playbook's USE SKILLS line names `why`. A playbook never holds a "Load the" phrase (ADR 0028) |

`unslop` is the base layer: every other skill points to it, and it points to none.

## Part 3: Where a stage loads one of them
A stage loads `technical-writing` only where a person decides from what it wrote; the standing rule covers every
other reply. A stage never loads both: `technical-writing` applies `unslop` itself.

| Moment | Who reads it | Stage |
|---|---|---|
| Intent | product owner | `aidlc-intent`, writing `intent.md`; it also loads `in-your-own-words` at its first step |
| Ready | product owner | `aidlc-specify`, before asking for Ready |
| Design + plan | tech lead | the stage that writes the design or the plan document a person approves (`aidlc-design`, `aidlc-plan`) |
| Merge | code owner | `aidlc-review`, writing the pull request description |
| Release | release approver | `aidlc-release`, writing the readiness record and the change record |
| Incident | on-call | `aidlc-operate`, writing the incident note and the follow-up work item |
| Discovery | engineer | `aidlc-discover` loads `how` and `why` where it traces a path |

Each is one "Load the `<name>` skill." line at the step that writes the document. `aidlc-build` and `aidlc-verify`
load none: what they write for a person is a stop message or the evidence table, which the standing rule covers.

## Part 4: Boundaries, so the AI loads the right one
| Pair | The line between them |
|---|---|
| `writing-documentation` and `technical-writing` | `writing-documentation` decides which document, for which reader, where it lives and what mode (Diátaxis). `technical-writing` decides how its sentences read |
| `committing-changes` and `reviewing-code`'s change descriptions, and `technical-writing` | `committing-changes` decides what a commit or a pull request holds (one reason per commit, a typed subject, a body that says why, a reviewable size), and `reviewing-code` what a change description must cover. `technical-writing` decides how those sentences read |
| `technical-writing` and `unslop` | `technical-writing` shapes a draft; `unslop` is the last pass on any text, and the only owner of the AI-tells catalog |
| `how` and the `explorer` agent | The agent answers one precise question with citations. `how` frames the question and turns the answer into a mental model |
| `how` and `why` | How it works now, from the code; why it is like this, from the history. Each description names the other |
| `in-your-own-words` and the stages' own restatements | The stages restate the outcome and criteria of a story (`aidlc-plan` step 1, `aidlc-build` step 2), and those steps stay as they are. `in-your-own-words` restates a person's request before there is a story |

Every new description stays below the routing check's 0.75 similarity with every other skill's
(`scripts/route_check.py`), and the routing cases gain one case per new skill.

## Part 5: What these skills never do
- Never change code, commands, file paths, identifiers, quoted text, test output or a template's fixed lines.
- Never a gate: text that breaks a rule is a low review finding, never a stop.
- Never change what a sentence says to make it plainer: meaning first.

## Kept, unchanged
- Every gate, decision and stop; the ten stages' identical hand-off and LANE lines; the stages' restatement steps.
- `aidlc-onboard` is not changed and nothing new depends on it.

## How it is tested
- **Structure tests:** each new skill's sections, its pstack credit and its catalog's stable numbering; each caller's
  line (the standing rule, the four last-pass lines, the two playbook lines, the stage loads); `unslop`
  calls no other skill; the Diátaxis step in `writing-documentation`; the practice map lists the five.
- **The validator and the routing check:** the five pass as practices; no pair of descriptions at or above 0.75.
- **Behaviour evals** (written, run when an API key or token is available): `unslop` cleans a paragraph full
  of AI tells and leaves its code block and command byte for byte; `why` answers from a scaffold's commit
  history, cites a commit and marks an inference.
- **Existing tests:** `scripts/test_loads.py` pins each stage's loads, so every new load line changes an expected set,
  and some skills are near their word limits (`aidlc-plan` 3,493 of 3,500; `story-run` 2,274 of 2,300; `lane-run`
  with `worker.md` 3,855 of 3,900). The plan lists each change for the owner's approval.

## Out of scope
- `bro`, `teach` and `ketchup`; pstack's tool skills and principle skills (a later review).
- Rewriting any stage's existing text to make it plainer.
- The future of `aidlc-onboard`.

## Risks
- **The wrong skill loaded.** Sharp descriptions, the 0.75 routing check and one routing case per skill.
- **A pass that damages technical text.** Part 5's rule, and an eval that checks a code block survives byte for byte.
- **Word limits.** Each stage gains one short line; the plan lists every limit it raises.

## The version
aidlc 8.2.0, a minor release: five new skills and the lines that call them; no gate changes.
