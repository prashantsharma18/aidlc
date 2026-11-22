# pstack's playbooks and principles: the concepts worth taking into aidlc

Read-only review, 2026-11-22. aidlc at local `main` (29a5b2a, aidlc 7.2.0). pstack is the local copy of
`cursor/plugins/pstack` (MIT, Lauren Tan). A few principle files are short. They match upstream, checked through
`gh api`. A pstack path is relative to `pstack/`, and `PB/` means `skills/poteto-mode/playbooks/`. An aidlc path is
relative to the repository root. `file:N` means line N.

This review goes below the structure. The first review (`pstack-vs-aidlc-review.md`) looked at how the pieces
connect, and it holds: aidlc's routes are its playbooks, so no new playbook files are needed. This review looks at
what each playbook and principle knows. Most of that knowledge belongs in aidlc's practices and stage steps, not
in new files.

## Verdict key

| Verdict | Meaning |
|---|---|
| ADOPT | New in aidlc. Worth adding. |
| STRENGTHEN | aidlc has a weaker form. Sharpen it. |
| ALREADY | aidlc covers it as well or better. No change. |
| SKIP | It conflicts with a fixed decision, needs host-only tools, or adds nothing for a team. |

"Lands in" names the smallest place the idea fits. Every landing keeps aidlc's gates as they are. Nothing below
lets the AI approve, merge, push or skip a person's decision.

## Summary

- **About 60 concepts and principles are worth taking.** 12 are ADOPT and 47 are STRENGTHEN (many small). 70 are ALREADY and 24 are SKIP. Most land in five places:
  `debugging-failures`, `aidlc-review` with `reviewing-code`, `aidlc-design` and `aidlc-plan`,
  `tuning-performance`, and `simplifying-code`.
- **The biggest gaps are in diagnosis and merge readiness.** aidlc has the steps for a failure (reproduce,
  localise, reduce, guard, fix). It does not say how to choose between causes, what to do when two fixes fail for
  the same reason, or that a refuted guess must be backed out. And nothing checks whether the default branch moved
  under a pull request after CI ran.
- **One idea changes how design works.** "A fork you could settle by running something: run it instead of asking"
  (`skills/poteto-mode/SKILL.md:21`, `PB/prototype.md`). aidlc's design has options and UNKNOWNs on paper. A short
  throwaway spike turns an UNKNOWN into a FACT before the tech lead decides.
- **About half of the concepts are already in aidlc, often in a stronger form.** Examples are tests first,
  small green steps, the lessons ladder, separate files per lane, reviewers with a fresh context, and the
  committed decision log.
- **Twenty-one items conflict with fixed decisions.** The agent merging, force-pushing, opening pull requests,
  posting replies, never asking a person, and "the bar in your brief is the whole bar" are all out. Section 5
  lists each one so it is not adopted by accident.

---

## 1. The playbooks, concept by concept

### 1.1 Bug fix (`PB/bug-fix.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Reproduce it yourself, on the surface where it fails.** Ask a person only with a stated reason the surface cannot be reached. If it will not fire, build the trigger, tighten conditions or add instrumentation until it does (`:7`). | `debugging-failures/SKILL.md:49-82` (reproduce, with a tree for "cannot reproduce"). Route D1 needs a reproduction (`using-aidlc:53`). | ALREADY | none |
| **Binary-search the cause through competing hypotheses.** Write the candidate causes. Each pass, take the test that rules out the most, get evidence from a run, and cross out the losers. Never guess (`:8`). | `debugging-failures:96-118` localises by layer and by `git bisect`. There is no list of competing causes and no rule for choosing the next test. Only `aidlc-operate:37` asks for competing hypotheses, and only in production. | STRENGTHEN | `debugging-failures`, a new step between Localize and Reduce: "Write two or more candidate causes, each with the observation that would rule it out. Run the one that rules out the most. Record what each run showed." |
| **Every shipped line traces to evidence. A change that "might help" is a guess, so it does not ship. When the evidence refutes a guess, revert what it motivated** (`:5`). | `aidlc-build:42` allows one targeted fix per attempt, three in all. `debugging-failures:272` flags "several unrelated changes made while debugging". Neither says to back out a failed attempt. | STRENGTHEN | `aidlc-build` step 8 and `debugging-failures` step 5: "Before the next attempt, revert the last one in full. A diff holds only the change the evidence supports." Without this, attempt three runs on top of the debris of attempts one and two. |
| **Confirm the mechanism with evidence before you plan the fix** (`:8`, last sentence). | `debugging-failures:146-161` says to fix the root cause and keep asking why. It does not ask for proof of the mechanism before the fix. | STRENGTHEN | `debugging-failures` step 5: "Name the mechanism, and show the run that proves it, before you write the fix." |
| **Regression history: read the record, not only the code.** Seed the hypotheses with the commits and pull request talk that changed the area (`:8`, via the `why` skill). | `debugging-failures:110-118` uses `git bisect`, which finds the commit, not the reason. | STRENGTHEN | `debugging-failures` Localize: "For a regression, read the commits and pull requests that touched the area (`git log -L`, the review threads). Cite what the authors wrote and mark your own inferences." |
| **"Inconclusive" or the wrong surface is not a pass. Unit tests show branch behaviour, not that the bug is gone** (`:10`). | `debugging-failures:284` ("the original bug scenario is checked end-to-end"). `aidlc-verify:32` (a skipped test is never a pass). | ALREADY | none. The structural review's "Drive the app" item (its rank 4) closes the rest. |
| **The failing reproduction lands before the fix in git history** (`:11`). | `aidlc-build:40`: the reproducing test fails first, and commits come one per green step. | ALREADY | none |

### 1.2 Feature (`PB/feature.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **The throughput checkpoint, four items, none dropped.** (1) blocking first steps run before fan-out; (2) independent workstreams: disjoint files parallelise, shared writes serialise; (3) shared mutable state: split it first; (4) the smallest safe split, or say why one worker is best. An item that does not apply stays, written `n/a: <reason>` (`:7-11`). | `aidlc-plan:64-69` (slicing, independent slices), `references/independent-slices.md` (DEPENDS ON, one slice per branch, separate files per slice), `parallel-lanes` (the coordinator holds back clashing rows). Items 1 to 3 are covered. Item 4 and the `n/a: <reason>` rule are not. A plan that keeps one branch never says why. | STRENGTHEN | `aidlc-plan` step 5 and the plan template's ORDER field: "ORDER says which slices must come first, which could run apart, and what they share. If all slices stay on one branch, say why in one line." The tech lead then sees that parallel work was considered. |
| **Name the data shape before any logic is written.** The delegate's scope names the shape (a state machine, not scattered booleans; a table, not branches; a typed model) (`:12`). | `aidlc-specify:40` lists entities, states and events. `reviewing-code:96-110` names the remedy after the fact. The bundle has PATTERN (`task-bundle.md:22`), an example to copy, but no shape. | STRENGTHEN | The task bundle: add the shape to DO step 1, or a SHAPE line: "the structure this slice introduces (state machine, typed model, lookup table), or none". A delegate slice then makes fewer judgement calls, and the decision log gets shorter. |
| **Review separation is mandatory: the writer never grades its own work** (`:12`). | `aidlc-build:103`, `aidlc-review:39`: only a non-author verdict counts, from reviewers in a fresh context. | ALREADY | none |
| **Port a shared-primitive fix to every consumer, and verify each** (`:12`). | none for a shared helper inside the repository. `migrating-safely:103-127` covers external consumers. | STRENGTHEN | `simplifying-code` and `debugging-failures` (see 1.9): "When you fix a shared helper, find every caller. A caller outside MAY CHANGE is a stop, never a quiet edit." |
| **Verify on the matching surface. The wrong surface is flagged, never passed** (`:13`). | `testing-in-browser` for web pages. Verify reads CI (structural review item X8). | ALREADY in part | Structural review rank 4 ("Drive the app") |
| **Small ordered commits; stack follow-ups** (`:14-15`). | `committing-changes:24-25`, `aidlc-build:41`. | ALREADY | none |
| **A contested design goes to a challenge pass before shipping** (`:16`). | `stress-testing-decisions` at Tier 2 and above (`aidlc-plan:63`, `aidlc-design:49`). | ALREADY | none |
| **Code-coupled work goes to one owner. Parent-level fan-out is only for independent artefacts. Spawn a fresh owner rather than chain interrupts** (`:19`). | `aidlc-build:27` (a fresh session per slice), ADR 0025 (lanes only for independent slices). | ALREADY | none |

### 1.3 Prototype (`PB/prototype.md`, and `skills/poteto-mode/SKILL.md:21`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Settle a fork by running something instead of asking** (`poteto-mode:21`). | none. `aidlc-design:48-49` frames options on paper and labels each impact FACT, INFERENCE or UNKNOWN. `aidlc-discover:38` asks the person for runtime evidence. Nothing says "run a small experiment to turn an UNKNOWN into a FACT". | ADOPT | `aidlc-design` steps 3 and 4, and `aidlc-discover` step 3: "When an UNKNOWN is a fact a short run can settle (how a library behaves, a query plan, a timing, how a layout feels), run a throwaway spike, read `references/spike.md`, and cite what it showed as FACT. A question of product, risk or approval goes to its owner." |
| **No decision, no prototype.** Name the decision it must make first (`:7`). | none | ADOPT | `references/spike.md` step 1: "Write the question and what result would change the choice. If you cannot, there is nothing to spike." |
| **Throwaway, isolated from production source. The lightest stack that answers the question** (`:9`). | none | ADOPT, with aidlc's limits | `references/spike.md`: in a scratch folder outside the repository's source, never committed to the story's branch. Only tools already installed. A package to fetch is a new dependency and asks first. Time-boxed, like discovery (`aidlc-discover:35`). |
| **Compare variants side by side behind one switch** (`:10`; `principle-exhaust-the-design-space`). | `aidlc-design:48` asks for two real options, on paper. `building-user-interfaces:126-133` studies references. | STRENGTHEN | `references/spike.md`: for a new screen or interaction with no example in the product, build two or three variants behind one switch. Screenshot each. The product owner picks, as the wireframe rule says (`aidlc-design:44-47`). |
| **The observation is the test.** Screenshot, log the timing, print the output (`:11`). | `testing-in-browser:35` ("look at every screenshot"). | ALREADY in spirit | `references/spike.md` cites the observation, not an opinion. |
| **The output is the decision plus the throwaway, never shippable code.** The real build follows the normal route (`:12`). | none | ADOPT | `references/spike.md`: "A spike's code never moves into the build. The design note links the observation, and the build writes the real thing, tests first." |

### 1.4 Investigation (`PB/investigation.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Read-only. A cited explanation, not a code change** (`:5`). | `aidlc-discover` (the evidence pack), the `explorer` agent (`agents/explorer.md:9`). | ALREADY | none |
| **A fixed output shape: overview, key concepts, how it works, where things live, gotchas, or a recommendation with a tradeoffs table** (`:9`). | `aidlc-discover` uses the evidence pack template. Outside a story, no shape is given. | SKIP | A question outside a story needs no aidlc route. A plain session answers it. |
| **If it turns into a code change, hand back and re-route** (`:12`). | `aidlc-start` and `references/re-routing.md`. | ALREADY | none |
| **For "why is it like this", read the record (the `why` skill)** (`:7`). | `aidlc-discover:37` traces callers, callees, data, events and configuration. History is not one of the directions. | STRENGTHEN | `aidlc-discover` step 3: add a sixth direction, history. Read the commits, pull requests and ADRs that shaped the area, cite them, and mark inferences. |
| **Push back when the premise is wrong; give a real judgement** (`:14`). | `reviewing-code:252-260` (honesty), `stress-testing-decisions:24` (brief it to oppose). | ALREADY | none |

### 1.5 Perf issue (`PB/perf-issue.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Capture a baseline on the real surface, and vet every number** (`:5`). | `tuning-performance:36-77` (measure first, synthetic and field). | ALREADY | none |
| **The performance mantras, cheapest first, and stop at the first that meets the target:** don't do it; don't do it again; do it less; do it later; do it when they're not looking; do it concurrently; do it cheaper (`:7-16`). | `tuning-performance:127-143` lists anti-patterns by layer. It has no order of remedies. | STRENGTHEN | `tuning-performance` step 3: "Try the remedies in this order: remove the work, avoid repeating it, do less, defer it, move it off the user's path, run it in parallel, then make it cheaper. Stop at the first that meets the target." Removing work is usually simpler and safer than making it faster. |
| **Don't claim a ceiling without running it** (`:6`). | `tuning-performance:226` ("If you haven't measured, you don't know"). | ALREADY | none |
| **Parse the artefacts into a queryable form and diff them** (`:19`). | none | SKIP | Tool-specific. Pointing at the repository's own profiler is enough. |
| **Cite the measurement in the pull request** (`:20`). | `tuning-performance:159` (the commit message holds the before and after numbers), `:178` (the ledger in the pull request description or `PERF.md`). | ALREADY | none |

### 1.6 Hillclimb (`PB/hillclimb.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **One change, one measurement, keep or revert. Never stack untested changes** (`:5`). | `tuning-performance:145-166` (keep-or-revert table, "neutral is a revert", one change at a time). | ALREADY | none |
| **Pick a case that reproduces the complaint. If none does, fix the reproduction before you optimise** (`:7`). | `tuning-performance:79-103` lets the symptom decide where to measure. It does not require a case that reproduces the complaint. | STRENGTHEN | `tuning-performance` step 1: "Measure a case that shows the reported slowness. If no case shows it, the reproduction is the first job." |
| **A stop predicate pairs a target with a floor on attempts, so a lucky early win cannot end the run** (`:7`). | none | SKIP | That suits an open-ended loop. In aidlc the target is the criterion's number in the spec, and the slice ends at DONE WHEN. |
| **Build the harness, prove it can tell cases apart, then freeze it. It prints its error count and its work count** (`:8`). | none. `tuning-performance:149` asks to re-measure "the same way". | STRENGTHEN | `tuning-performance` step 1: "Before the first change, show the measurement separates a slow case from a fast one. Then do not change it during the work. Changing the harness mid-run is changing the assertion." This is aidlc's "the bar never drops", applied to a harness. |
| **The decision log, one row per attempt, read before each attempt** (`:9`). | `tuning-performance:168-178`: the ledger, kept and reverted alike, read before the next experiment. aidlc commits it. pstack keeps it out of git, which is weaker for a team. | ALREADY (better) | none |
| **Each hypothesis names a mechanism, never "try memoizing something"** (`:10`). | `tuning-performance:129` (fix the one thing step 2 found). | ALREADY | none |
| **Push past the first plateau: change category, combine near-misses, re-read the source** (`:17`). | none | SKIP | It conflicts with aidlc's three-attempt stop when the "attempts" are failures. For pure performance work the ledger already stops repeats. |
| **Correctness and simplicity outrank the number. Keep a simplification that holds the number** (`:17`). | `tuning-performance:162,166` ("a regression wearing a win's clothing"; correctness gates the metric). | ALREADY | none |

### 1.7 Runtime forensics (`PB/runtime-forensics.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Capture a real artefact (profile, heap snapshot, trace), never theorise from source** (`:5`). | `tuning-performance:123-124` (heap snapshot, CPU profile), `debugging-failures:227-234` (instrumentation). | ALREADY | none |
| **Reduce the artefact to the smoking gun: the hot function, the retainer chain** (`:6`). | none, in so many words | STRENGTHEN | `tuning-performance` step 2, one line: "Reduce the profile to the one function or retainer chain that holds the time or the memory, with its file and line." |
| **Prove the mechanism cheaply before you believe it: inject instrumentation into the running process** (`:7`). | `debugging-failures:227-244` (add logging only when it helps). | STRENGTHEN, local only | Merged with 1.1's "confirm the mechanism". Never on production: `aidlc-operate:35` gives the AI no production access. |
| **Map the finding back to source: file, symbol, line** (`:8`). | `aidlc-plan:53`, `aidlc-discover:37` (every finding with `file:line`). | ALREADY | none |
| **The deliverable is a diagnosis, not a fix. Hand back to Bug fix or Perf** (`:3,11`). | `aidlc-operate` (diagnose; a new work item enters at `aidlc-start`). | ALREADY | none |

### 1.8 Trace forensics (`PB/trace-forensics.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **The capture is a fixed dataset: read it, don't re-run it** (`:5`). | `aidlc-operate:35` (a person runs steps; you read what they share). | ALREADY | none |
| **Get the artefact into a form you can query before you read it** (`:8`). | none | SKIP | It depends on the tool. |
| **A frame with no source mapping is not yet a diagnosis** (`:10`). | `ops-diagnoser:12-13` (each entry has a source, each hypothesis is labelled). | ALREADY | none |
| **Without a paired before-and-after capture, it is the strongest hypothesis, not a confirmed cause** (`:11`). | `aidlc-operate:37`: "A cause stays a hypothesis until a named person confirms it". | STRENGTHEN, small | `ops-diagnoser` Work: "Mark a cause confirmed only with a paired capture, before and after. Otherwise rank it as the strongest hypothesis." This gives the person who confirms a standard. |

### 1.9 Refactoring (`PB/refactoring.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Pin the contract first. A characterisation test, a snapshot or an equivalence harness. A type check and a lint run are not a pin** (`:7`). | `simplifying-code:21` (pin the behaviour; characterisation tests). It does not say a type check is not a pin. | STRENGTHEN, small | `simplifying-code` step 1: "A type check or a lint run is not a pin. Only a test of behaviour is." |
| **Name the missing structure. The reshape must delete branches or invalid states, not add indirection** (`:8`). | `simplifying-code:22-30`, `reviewing-code:68` ("reduce or just relocate?"). | ALREADY | none |
| **Subtract before you add: a subtraction commit first** (`:10, :14`). | `simplifying-code:16` ("simplify first, in its own commits"), `:30` (delete dead code). Commit order is not stated. | STRENGTHEN | `simplifying-code` step 4: "Commit the deletions first, then the reshape, then the follow-on tidy-up. Each stays green." Deletions are the easiest commit to review, and they make the reshape smaller. |
| **Migrate every caller of an internal API and delete the old one in the same wave. No shims, no parallel paths. Spot-check every rename in strings, docs and back-references** (`:11`). | `migrating-safely:103-127` covers deprecation across consumers, step by step. Nothing covers an internal API inside one repository, or rename leftovers. | STRENGTHEN | `simplifying-code`, a new step: "For an internal API with no outside users, move every caller and delete the old one in the same slice. Then search for the old name in strings, docs, config and tests. A caller outside MAY CHANGE is a stop." An external or published API stays with `migrating-safely` and its expand and contract steps. |
| **Prove nothing changed with an equivalence check: a script that diffs old and new outputs, or a recorded baseline replayed** (`:12`). | `simplifying-code:32` compares before and after for every kind of input, by reasoning. | STRENGTHEN | `simplifying-code` step 5: "For a large reshape, write a small script that runs old and new on the same inputs and diffs the outputs. Keep its output in the hand-off." That is the "build the lever" principle in practice. |
| **The success measure is a lighter load on the reader. A refactor that does not lower it is reverted** (`:13`). | `reviewing-code:346,361` (a refactor that only moves code is a red flag). | STRENGTHEN, small | `simplifying-code` Checks: "Name what got simpler: fewer layers to trace, or less state to hold. If you cannot, revert." |
| **A bug found during the refactor is split out. The structural change ships first** (`:5`). | `simplifying-code:53` ("A refactor and a fix in one commit hide each other"). | ALREADY | none |

### 1.10 Visual parity (`PB/visual-parity.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **The baseline comes first: screenshots of each state before the migration. No baseline, no claim of parity** (`:5`). | `testing-in-browser:34-35` takes screenshots after the change, and a person looks. There is no "before" set. | ADOPT | `testing-in-browser`, a new section: "For a change that must not change how a page looks (a refactor, a framework or design-system upgrade, often route S), record screenshots of each changed screen and state before the change, with the repository's visual comparison tool." |
| **Image diff, not the eye. A nonzero diff is a fail** (`:3,8`). | `testing-in-browser:35` (look at every screenshot). | ADOPT | Same section: "Compare by image diff. A difference fails until someone explains it." |
| **No harness changes, no baseline tampering, no restructuring to make a diff pass. If the baseline looks wrong, stop and ask** (`:6`). | aidlc's assertion rule (`aidlc-build:59`) covers tests, but a screenshot baseline is not named. | ADOPT | Same section: "A baseline image is an assertion. Never update one to pass: its owner decides, as for any assertion (AMENDED ASSERTIONS)." With no comparison tool in the repository, propose one as a dependency, which a person approves. |
| **Shared primitives migrate first, as a blocking phase. Then one component at a time** (`:7`). | `aidlc-plan:64` (slice order). | ALREADY | none |

### 1.11 Eval (`PB/eval.md`)

aidlc's behaviour evals are owned by the framework owners (`evals/README.md`). A team also writes eval cases
through `aidlc-feedback:39` ("an eval case wherever an agent mistake could recur").

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Blinding: no "eval", "test", "judge", "rubric" or "benchmark" in any name or prompt the candidate sees. The prompt reads like an organic request** (`:7-10`). | The case prompts read like real requests (`evals/gate-scope/prompt.md`), but no rule says so. | STRENGTHEN | `evals/README.md` (framework standard) and `aidlc-feedback` step 3 (a team's eval case): "A case prompt reads like a real request. No name or path the agent sees says it is a test." |
| **Grade chain-following from what the agent did, never from its own account. Don't ask it to list the skills it used** (`:9, :22`). | `evals/README.md:16` grades behaviour: files written, tools called, the reply. | ALREADY | none |
| **Compare two variants with one judge, one pass, one scale, blind to which is which** (`:13`). | The baseline arm (`--ablation`) compares with and without the plugin. | ALREADY in part | none |
| **Read every output yourself, and compare it with the judge** (`:23`). | `evals/README.md:58` ("A low score is a finding about the kit"). | STRENGTHEN, small | `evals/README.md`: "Before a release, read a sample of the failed runs yourself. A grader that disagrees with your reading is a finding." |
| **Multi-model panels and judges from another model family** (`:20-21`). | none | SKIP | It depends on model names and the host (first review, section 4). |

### 1.12 Opening a PR (`PB/opening-a-pr.md`, `skills/poteto-mode/worker.md:9-11`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **The body is a one-minute briefing, under 40 lines. Long evidence goes in a linked file** (`:7`; `worker.md:11`). | `aidlc-review/assets/pr-description.md` (42 template lines). The decision log is copied in full (`aidlc-review:38`), and it can grow long. | STRENGTHEN | The pr-description template: "Keep the description to what a reviewer reads in a few minutes. Long tables (a long decision log, the full evidence) are linked from `plans/<KEY>/`." Keep the owner grouping, so each owner still finds their rows. |
| **A "Blast Radius" heading: who and what the change can reach** (`:7`). | `pr-description.md:16` has "Not changed". The evidence pack lists dependants, but only when discovery ran. Nothing in the description says what the change can break. | ADOPT | The pr-description template: a "Reach" section. The callers, consumers, jobs and data the change can affect, from the evidence pack or from a search, each with its reference. |
| **A "Tradeoffs" heading: only the rejected options a reviewer would ask about** (`:7`). | `plan.md` REJECTED (`aidlc-plan:59`). It is not shown in the description. | STRENGTHEN | The pr-description template: copy the plan's REJECTED lines that a reviewer would ask about, or link them. |
| **The title names a real symbol when one carries the change** (`:7`). | `committing-changes:26-29` (typed subject). | ALREADY | none |
| **Work from a worktree off trunk, and keep unrelated work out** (`:5`). | `parallel-lanes`, MAY CHANGE. | ALREADY | none |
| **The agent opens the pull request, ready, not draft** (`:9`). | `aidlc-build:44`: the person pushes and opens it. | SKIP | Conflict (section 5). |

### 1.13 Babysit (`PB/babysit.md`, `skills/poteto-mode/references/bugbot-triage.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Order of work: conflicts, then threads, then CI. A conflict is reported with the branch that needs the rebase. Say which callers trunk added to code the stack moves (the drift sweep)** (`:8`). | none. No stage looks at the default branch after CI ran. | ADOPT | `aidlc-review` step 8 (see 1.15, "drift check before Merge"). |
| **A flaky check earns one fresh build. Only the diff's own failures get a commit** (`:8`). | `aidlc-verify:47,54`: a red check is reported as it is. `writing-tests:50`: never re-run a flaky test until it passes. | STRENGTHEN, small | `aidlc-verify` step 1: "When a red check fails on a path the diff does not touch, say so, and check whether it also fails on the base. The person may re-run it once. A second red is a finding, and the change still does not pass." This separates "our change broke it" from "the base is broken" without lowering the bar. |
| **Judge bot comments on their merits. Fix the real ones, dismiss noise with a concrete disproof, escalate billing, data, auth and security** (`:9`; `bugbot-triage.md`, Decision rubric). | `aidlc-review:40` (a disposition for every finding: fixed with its commit, or dismissed with a reason; the engineer decides). | STRENGTHEN | `aidlc-review` step 4: "A dismissal cites its disproof: a file and line, a test, or a command and its output. 'Not an issue' is not a reason." |
| **A learned list of noise patterns: a name, a confidence level (candidate, recurring, strong), "skip when", "do not skip when", an example, a source. Security, data, migration and concurrency findings are never on it** (`bugbot-triage.md`, Learned pattern format and Ask by default). | `aidlc-feedback:48` routes lessons from repeated review findings, but only toward new checks. Nothing helps with a finding that keeps being dismissed. | ADOPT | `aidlc-feedback` step 4: a "Known review noise" section in the team's `AGENTS.md`, drafted for its owner, in that format. `aidlc-review` step 4 may then draft "dismissed: matches <pattern>, AGENTS.md". The engineer still decides each finding, and the never-on-the-list categories stay. |
| **Push the fix before you reply, so the reply cites the commit** (`:9`). | `aidlc-review:40` (fixed, with the commit). | ALREADY | none |
| **Declare a mode first: drive, threads-only, or check** (`:5`). | none | SKIP | aidlc's stages already fix what each run does. |
| **Owner approval is a wait. Babysitting never authorises a merge** (`:10`). | ADR 0023, `aidlc-review:53`. | ALREADY | none |
| **The agent rebases, replies through the API, resolves threads** (`:7, :9`). | Posting asks the person first (`aidlc-review:59`). | SKIP | Conflict (section 5). |

### 1.14 Shipping (`PB/shipping.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Only a verdict from an agent that did not write the code counts. Green CI and an approving bot are not verdicts** (`:5`). | `aidlc-build:103`, `aidlc-review:62,65`. | ALREADY | none |
| **A verdict covers a patch, not a commit. Compare `git patch-id` after a rebase; if only the base moved, the verdict can stand** (`:7`). | `aidlc-review:67`: any later commit that changes a path outside `plans/<KEY>/` voids the verdict. That includes a rebase. | SKIP for now | It would loosen a gate, so it needs a design change and an ADR (AGENTS.md, Boundaries). It would save a reviewer re-run after a clean rebase. Revisit if re-runs after rebases become a cost. |
| **Land the verified run bottom-up. A verified pull request above an unverified one waits** (`:6`). | `references/stacked-slices.md:10-13`, ADR 0025 (a stacked pull request merges after its parent). | ALREADY | none |
| **Read the pull request back after a merge. A queued merge or an armed auto-merge is not a merge** (`:8`). | `aidlc-review:44-55` (checks the approval in the review tool), `aidlc-release` reads the `merged` row. | ALREADY | none |
| **The agent merges, arms auto-merge, retargets and force-pushes** (`:8`). | — | SKIP | Conflict (section 5). |

### 1.15 Autopilot-full and Autopilot-stack (`PB/autopilot-full.md`, `PB/autopilot-stack.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Drift check right before merge.** Fetch the default branch and ask whether its changes can affect the patch: a file both sides changed, a caller of the patch, a dependency version, or a change to which checks run. If so, the tested code is not what would land: rebase and run CI again. Otherwise merge without churn (`autopilot-full:19`). | none. `review-evidence.md:18` records BASE when the evidence is written. Nothing compares it with the default branch at Merge. A green pull request can still break the default branch once merged. | ADOPT | `aidlc-review` step 8, before "ready to merge": "Fetch. List the commits on the default branch since BASE. If any touch a file this change touches, a caller of a symbol it changes, a dependency or lock file, or the CI configuration, say which. Recommend that the person update the branch and let CI run again. Otherwise say the base is current enough." The person still updates and merges. |
| **Block only for a problem you can show: a failing run at the head, or a doc line the change made wrong. A problem the base already has does not block, unless the change copies it or newly reaches it. Everything else is a follow-up** (`autopilot-full:16`; `worker.md:6`). | `reviewer-bug:16` ("a finding is a fact you can show"). `reviewing-code:199-212` has severities, but no rule for a defect that already exists on the base. | STRENGTHEN | `reviewing-code` Step 5 and the four reviewer agents: "A defect the base already has is not this change's finding, unless the change copies it or newly reaches it. Report it in one line as a follow-up, which becomes a new work item at `aidlc-start`." It keeps scope stable and stops review from blocking on old debt. |
| **Anything that loosens a gate (a raised budget, an allowlist entry) needs a verifier's proof and a fresh countersign, because the owner wants green. A disabled or soft-failed check always comes out** (`autopilot-full:20`). | `aidlc-build:60` (a Quality bar exception carries a reason, an owner and an expiry, and a person approves it in the pull request). | ALREADY (better) | none |
| **Assume the machine dies: push each finished unit before the next, and keep a trail** (`autopilot-full:12`). | Commits per green step and the progress note (`aidlc-build:41,102`). The person pushes. | ALREADY | none |
| **Judge an agent by its side effects, never by its status text** (`autopilot-full:22`). | `parallel-lanes` reads each row's state from git and the index. | ALREADY | none |
| **Stand down at once on the operator's stop: zero writes** (`autopilot-full:23`). | none explicit | STRENGTHEN | Merged with Pause safely (1.17). |
| **Stop at verified; hand over to the operator; nobody pushes without a go** (`autopilot-stack:5`). | This is aidlc's default (ADR 0023). | ALREADY | none |
| **The agent merges under a grant; its countersign is the approval** (`autopilot-full:3,8,17,20`). | — | SKIP | Conflict (section 5). |

### 1.16 Autonomous run (`PB/autonomous-run.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **State the exit condition as a checkable predicate before the first step** (`:5`). | The bundle's DONE WHEN (`task-bundle.md:33`), "checks that must pass". A delegate slice runs to DONE WHEN or the first STOP IF (`tiers-table.md:14`). DONE WHEN can still be written as prose. | STRENGTHEN | `aidlc-plan` step 7 and the plan checklist: "Each DONE WHEN item is a command and the result it must show." See 1.19 for the live and performance checks. |
| **Each step makes the smallest change the evidence justifies. Keep what advanced, discard what didn't. "Might help" gets reverted** (`:7`). | `aidlc-build:41` (one green step at a time), `tuning-performance:160-164`. | ALREADY | none |
| **Never relax the predicate to declare victory** (`:11`). | `aidlc-build:60` (never lower the Quality bar), `evals/README.md:58` (never weaken a grader). | ALREADY | Named as a principle ("The bar never drops", section 3). |
| **Surface only irreversible actions, product calls no experiment can settle, or a real dead end** (`:9`). | aidlc's stops are the decisions table plus each stage's Stop if (ADR 0026). | SKIP as written | The aidlc-safe half ("a fact a run can settle, run it") is in 1.3. |
| **Fix mid-run discoveries yourself, in their own pull request** (`:9`). | Out-of-scope work is a stop or a new work item (MAY CHANGE). | SKIP | Conflict (section 5). |
| **Wake on events with `/loop` and watcher sub-agents** (`:6`). | — | SKIP | Host-only (ADR 0024). |

### 1.17 Pause safely (`PB/pause-safely.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Pause only when asked. "Keep going" never pauses** (`:3`). | aidlc pauses only where the MODE, the decisions table or a stop says (`aidlc-build:41`). | ALREADY | none |
| **Stop at a safe boundary: finish the current step or back out of it. Start nothing new. Cancel nested sub-agents** (`:5`). | none. The STATUS values (`progress-note.md:9`) cover checkpoints and stops, not a person saying "stop now" in the middle of a step. | STRENGTHEN | `aidlc-build` Rules: "When the person asks you to stop, finish the current step if it can go green quickly. Otherwise back it out to the last green commit. Start nothing new." |
| **Take no irreversible action to pause** (`:6`). | The AI holds no push credential (`tiers-table.md:61`). | ALREADY | none |
| **Make the work durable with one `wip:` commit, even on a broken tree** (`:7`). | `committing-changes:25,59` (every commit builds and passes; "wip" is a red flag). | SKIP the wip commit | A red commit on the story's branch breaks the bisect rule. Back out to the last green commit instead (row above). |
| **A resume note: intent, what you were doing, what is verified, state, next steps, key files, gotchas. Point at the trail instead of copying it** (`:8`). | The progress note already holds most of this (Session plan, Deviations, Assumptions, Context gaps). It has no "next action" line. | STRENGTHEN, small | `progress-note.md`: a `RESUME AT` line ("the next step's number, and what was learned that the note does not yet say"), written at any stop and at a requested pause. STATUS `stopped: paused by <person>`. |

### 1.18 Session pickup (`PB/session-pickup.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **The prior trail is authoritative. Rebuild the state from it, don't re-derive it** (`:6`). | `aidlc-build:27,102` (a new session rebuilds the state from the bundle, the progress note and the commits). | ALREADY (better: git, not chat) | none |
| **Compare done with planned. Name the resume point. Never redo completed work** (`:7`). | Implicit. The Session plan checkboxes (`progress-note.md:21-22`) and `git log`. Nothing says to reconcile the two. | STRENGTHEN, small | `aidlc-build` step 1 for a resumed slice: "Match each checked step in the note with its commit. A checked step with no commit is not done. A commit with no checked step is a step to record. Resume at the first step with neither." |
| **Verify inherited claims against the goal. A passing self-report is not proof** (`:9`). | `aidlc-build:35` re-runs the tests before any change. `aidlc-build:103` (a verdict only from a non-author). | ALREADY | none |
| **Read the chat transcripts from the host's folders** (`:5`). | — | SKIP | Host-specific and private. aidlc's state is in git (first review, section 4). |

### 1.19 Multi-phase plan (`PB/multi-phase-plan.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Skip the plan when the change is one or two files with an obvious approach** (`:5`). | Routes F0, D1 and S (briefs). | ALREADY | none |
| **Settle open questions by prototype before writing the plan. Ask only about product or preference calls** (`:6`). | `aidlc-plan:52` sends ambiguities to the criterion's owner. A technical UNKNOWN gets an owner (`:53`). | STRENGTHEN | `aidlc-plan` step 2, through the spike reference (1.3): a technical UNKNOWN a short run can settle is settled before the plan is drafted. |
| **Open with the landing order and the dependency graph: which are independent, which wait, the files each may touch** (`:7`). | ORDER, DEPENDS ON, MAY CHANGE (`plan.md`, `task-bundle.md`). | ALREADY | none |
| **Each unit has evidence checkboxes: unit, live and performance. Tests alone are not enough. A live box drives the real surface with a scenario and a pass predicate. A perf box names the metric, the probe, the baseline measured on trunk first, and the number that fails** (`:8`). | DONE WHEN (`task-bundle.md:33`). `aidlc-design:55`: every non-functional requirement has a test, check or monitor. Nothing puts the live or performance check into the slice that changes it, and nothing requires the baseline before the change. | STRENGTHEN | The task bundle's DONE WHEN, and `aidlc-plan` step 7: "For each criterion users see, a live check: the scenario and what passes. For each performance criterion: the metric, how it is measured, the baseline measured on the default branch before the slice starts, and the number that fails." `aidlc-verify` step 2 then has a row for each. |
| **A change to an interaction waits for the operator's review** (`:8`). | The wireframe rule (`aidlc-design:44-47`). | ALREADY | none |
| **Hand back the plan and stop. Execution starts on an explicit go** (`:9`). | Design + plan at Tier 2 and 3. At Tier 1 the plan is stated (ADR 0026). | ALREADY | none |
| **Say what stays unproven** (`:11`). | `aidlc-verify:34` (Unproved, with who accepted it). | ALREADY (better) | none |

### 1.20 Authoring a skill (`PB/authoring-a-skill.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Validate frontmatter, referenced files and links** (`:6`). | `scripts/validate.py`, `scripts/test_loads.py`. | ALREADY | none |
| **When in doubt, delete. Keep only prose that changes a decision** (`:10`). | Plan 26 shortened the stage skills. `aidlc-onboard:64-73` filters context ("Otherwise, leave it out"). | ALREADY | none |
| **Delegate to other skills by path. Don't restate** (`:10`). | aidlc repeats shared rules on purpose, so each skill holds alone (first review, X6). | SKIP | The named principles (section 3) give the shared vocabulary without removing the copies. |
| **"Tell it to do the thing and skip the reason"** (`:10`). | AGENTS.md: "Explain why, not only what." | SKIP | Conflicts with aidlc's writing standard. |
| **A workflow you keep hitting that no skill captures: propose a new skill** (`:10`). | `aidlc-feedback` routes lessons to the team's project. Framework owners own the skills (`docs/operating-model/roles.md:10`). | ALREADY | none |

### 1.21 Worktree cleanup (`PB/worktree-cleanup.md`)

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **Read worktree paths from `git worktree list`, never hand-typed** (`:3`). | `parallel-lanes:179-181` (compares `.worktrees/` with `git worktree list`). | ALREADY | none |
| **A tool's "safe" bucket is advice, not permission. The in-use set wins** (`:4`). | `parallel-lanes:181,265` (the person confirms a folder that may hold uncommitted work). | ALREADY | none |
| **Pause on irreversible loss. A clean, merged, unused worktree may go. Uncommitted work is shown and decided** (`:6`). | `parallel-lanes:171-172` (release removes the worktree, never `--force`; uncommitted work is committed or reported). | ALREADY | none |
| **Measure the space reclaimed; clear simulators and caches** (`:3, :8`). | — | SKIP | Personal-machine housekeeping, host-specific. |
| **`git worktree remove --force` and `rm -rf`** (`:7`). | `parallel-lanes:277` (`--force` is a red flag). | SKIP | Conflict (section 5). |

### 1.22 The mode file and the worker preamble (`skills/poteto-mode/SKILL.md`, `worker.md`)

These are not playbooks. Several of their lines carry concepts the playbooks rely on, so they are covered here.

| Concept | aidlc today | Verdict | Lands in |
|---|---|---|---|
| **First message: restate the goal and the smallest change that meets it** (`SKILL.md:19`). | `aidlc-build:36`, `aidlc-plan:52` (restate). "Smallest" is not said. | STRENGTHEN | Principle "Smallest change inside the boundary" (section 3). |
| **Name the principle that shaped each decision, and only one you read** (`SKILL.md:15`). | The decision log gives a reason per row (`aidlc-build:41`). | STRENGTHEN, small | When section 3 exists, a decision-log row may name the principle in its "why". |
| **Give each claim its evidence or a label: measured, inferred, or a guess** (`SKILL.md:104`). | FACT, INFERENCE, UNKNOWN throughout (`aidlc-plan:53`, `aidlc-discover:37`). | ALREADY | none |
| **Never hand the person a check you could run** (`SKILL.md:104`). | aidlc runs local checks. Production steps stay with a person by design. | ALREADY | none |
| **No is an acceptable answer. Candour over agreement** (`SKILL.md:82`). | `reviewing-code:252-260`, `stress-testing-decisions:49-50`. | ALREADY | none |
| **Fresh sub-agents by default, given the original brief, every later directive and the prior report** (`SKILL.md:100`). | Reviewers in a fresh context (`aidlc-review:39`). A rerun after a void verdict writes the evidence file again (`:67`). | ALREADY | none |
| **The worker preamble** (`worker.md`). | Structural review rank 3. | — | Not repeated here. |

---

## 2. The principles

aidlc's equivalent is the closest existing text. "Named" says whether it should become one of aidlc's named
principles (section 3).

| Principle | Rule and trigger, in one line | aidlc equivalent | Verdict | Named? |
|---|---|---|---|---|
| Attack the Premise | After two or more fixes that share one premise fail the same check, write the premise down and test it before any further fix. | `aidlc-build:42,73`: three attempts, then stop. Nothing says what to do between attempts two and three. | ADOPT | Yes, inside "Fix the cause" |
| Boundary Discipline | When wiring validation or adapters, guard at system boundaries, trust internal types and keep logic pure. | `designing-apis:97-110,390`, `securing-code:34,51-55`. | ALREADY | Yes, inside "Shape before logic" |
| Build the Lever | For non-trivial work, build the script or codemod that does or proves it. Do the first unit by hand, then prove the tool on it. | RECIPE and the recipe commit (`aidlc-plan:79`, `aidlc-build:39`). `aidlc-feedback` encodes checks. Nothing prompts a small equivalence or checking script. | STRENGTHEN | No. Lands in `simplifying-code` step 5 (equivalence script) and `aidlc-plan` step 7 ("a repeated edit across many files is a RECIPE"). |
| Encode Lessons in Structure | When an instruction repeats, encode it as a lint, flag, check or script. | `aidlc-feedback:29-46` (the ladder, proven on the past mistake). | ALREADY (better) | Yes |
| Exhaust the Design Space | For a decision with no precedent, build two or three competing prototypes and compare them. | `aidlc-design:48` (two real options, on paper). | STRENGTHEN | Yes, inside "Run it or ask its owner" |
| Experience First | Choose user delight over implementation convenience. The next maintainer is a user too. | The product owner owns intent and scope. `aidlc-design:44-47` (empty, loading and error states). | SKIP | No. Scope is the product owner's call, not the AI's. |
| Explain the Number | Before you trust or report a measured number, name its limiter and rule out that it measured something else. | `tuning-performance:145-178` (noise, keep or revert). There is no limiter, no error count and no "did the work run". | STRENGTHEN | Yes, as "Measure before you claim" |
| Fix Root Causes | When debugging, fix the first place the system went wrong. A guard is a fix only for a legitimate state. Fix every instance of the pattern. | `debugging-failures:146-161,223-225` (root cause, fallbacks are behaviour). Not covered: every instance, the legitimate-state test, the always-on signal. | STRENGTHEN | Yes, as "Fix the cause" |
| Foundational Thinking | Before logic, get the core types and data shapes right. Scaffold first. | `aidlc-specify:40`, route G slice 0. | STRENGTHEN | Yes, inside "Shape before logic" |
| Guard the Context Window | When context fills, send bulk to sub-agents and keep summaries. | The `explorer` agent (`aidlc-plan:53`, `aidlc-discover:37`), a fresh session per slice (`aidlc-build:27`). | ALREADY | No |
| Laziness Protocol | When sizing a diff or tempted by a layer, prefer deletion and the smallest change. One source of truth per decision. | MAY CHANGE, `simplifying-code:39` (no abstraction for one use). "Smallest change" is never said. | STRENGTHEN | Yes, as "Smallest change inside the boundary" |
| Make Operations Idempotent | For steps that may crash and retry, converge to the same end state. Derive each step from the state that exists. | `designing-apis:165` (idempotency keys), `stress-testing-decisions:26` (retry, duplicate), `parallel-lanes` claims. | ALREADY | Yes, inside "State lives in git" (a rerun reads the state and does only the difference) |
| Migrate Callers Then Delete Legacy APIs | With a new internal API and old callers, migrate and delete in one wave. No shims. | `migrating-safely:103-127` (external consumers, step by step). Internal APIs are not covered. | STRENGTHEN | No. Lands in `simplifying-code` (1.9). Its "delete tests that protect old details" is a conflict (section 5). |
| Minimize Reader Load | When code is hard to trace, count the layers and the hidden state. Collapse one-caller wrappers. The 30-second test. | `reviewing-code:68,106,346`. | ALREADY | No |
| Model the Domain | For stateful or branching logic, encode the domain in a structure (state machine, table, typed model). | `reviewing-code:100-105` (after the fact). The plan names no shape. | STRENGTHEN | Yes, inside "Shape before logic" |
| Never Block on the Human | On reversible work, proceed and let the person correct. | ADR 0026: a stage that is not a decision states what it did and goes on (`tiers-table.md:20-22`). | SKIP as written | No. aidlc's bounded form is "Run it or ask its owner". |
| Outcome-Oriented Execution | In planned migrations, accept planned intermediate breakage over throwaway compatibility code. | `aidlc-plan:64`: every slice starts and ends green. | SKIP | No. Conflict (section 5). |
| Prove It Works | Before saying done, check the real artefact, not a proxy. When a check fails, suspect the observation first. | `aidlc-verify` (the trusted run), `testing-in-browser:35,58`, the non-author verdict (`aidlc-build:103`). "Suspect the observation first" is missing. | STRENGTHEN, small | Yes, as "Prove it; someone else judges" |
| Redesign From First Principles | Integrate a new requirement as if it had been there from the start. Carry it through every reference. | `aidlc-design` amendment mode (`references/amendment.md`). | ALREADY in part | No. "Every reference" lands in 1.9's rename check. |
| Separate Before Serializing Shared State | When concurrent actors might write one target, give each its own. Lock only for a real invariant. | `references/independent-slices.md:11` (separate files per slice), `parallel-lanes` (git's lock, one worktree per row). | ALREADY (better) | No. It lives in `parallel-lanes`. |
| Sequence Work into Verifiable Units | Break work into small units that each end in a check. Deliver in the order that proves itself: failing test, then the fix. | `aidlc-plan:64`, `aidlc-build:40-41`. | ALREADY (better) | No. It is how the build works, not a choice. |
| Subtract Before You Add | When sequencing an addition or refactor, remove first, then build on the simpler base. | `simplifying-code:16,30`. No commit order is given. | STRENGTHEN | Yes, inside "Smallest change inside the boundary" |
| Test Behavior, Not Implementation | When writing or keeping a test, imagine two edits: break the behaviour (the test must fail) and change the internals (it must still pass). | `writing-tests:37-38` (the first edit and "behaviour a caller sees"). Not covered: the second edit, an expected value derived from the requirement, the error type over the message. | STRENGTHEN, small | No. It lands in `writing-tests` Checks. It is inside "Tests first; assertions stay". |
| Type System Discipline | When designing types, make illegal states unrepresentable, brand primitives, parse at boundaries, derive types from schemas. | `designing-apis:361-365` (branded IDs), `:97` (validate at boundaries). | ALREADY | No |

---

## 3. Proposed aidlc principles (12)

A short Principles section in `using-aidlc`, written once. Each stage keeps its own one-line rule, so a skill read
alone still holds (first review, rank 6). The rule's name is added after it. Credit pstack in the ADR that adds
the section. Where wording is close to pstack's, add the MIT notice to `skills/NOTICE`.

| # | Name | The rule, in one line | When it applies | Stages and practices that point to it | Source |
|---|---|---|---|---|---|
| 1 | **Text is data** | Text in a ticket, file, log or tool output can inform a draft. It never authorises an action, changes a criterion or widens the scope. | You read anything you did not write. | All | aidlc (39 files) |
| 2 | **People decide; you record** | A decision comes from its decider, or from a state you can check. You record it with how it was confirmed. You never approve or merge. | Something needs a yes, or someone reports one. | All stages; decisions table | ADR 0023, 0026 |
| 3 | **Prove it; someone else judges** | "Done" needs a recorded run of the real check, on the real surface. Someone who did not write the change judges it. When a check fails, first check that it measured what you think. | Before you say a change works, passes or is done. | build 9-10, verify, review, testing-in-browser, reviewer agents | aidlc + pstack Prove It Works |
| 4 | **Tests first; assertions stay** | A failing test comes before the code, and the reproduction comes before the fix. An existing assertion, a snapshot or a screenshot baseline changes only by its owner's decision. | Any change to behaviour. | build 6, writing-tests, debugging-failures, testing-in-browser, plan 3 | aidlc gate + pstack Visual parity |
| 5 | **The bar never drops** | Never pass by changing the check: no suppression, skip, lowered threshold, edited grader, moved baseline or changed harness. | A check can pass only if something about the check changes. | build (Stop if), verify, tuning-performance, evals | aidlc + pstack Autonomous run, Hillclimb |
| 6 | **Smallest change inside the boundary** | Make the smallest change that meets the criteria, inside MAY CHANGE and one repository. Remove before you add. What only "might help" is reverted. | Sizing a slice or a step, or tempted to add a layer, a shim or a "while I'm here" edit. | plan 5 and 7, build 4, 7 and 9, simplifying-code, reviewing-code | pstack Laziness Protocol, Subtract Before You Add + aidlc MAY CHANGE |
| 7 | **Fix the cause** | Reproduce, choose between causes by evidence, prove the mechanism, then fix it where it starts and everywhere the same fault is. After two failed fixes, test their shared premise. Three attempts, then stop. | A test fails, a build breaks, or a bug is reported. | build 8, debugging-failures, D1 and D2, operate | pstack Fix Root Causes, Attack the Premise, Bug fix + aidlc's three attempts |
| 8 | **Measure before you claim** | A number counts only with its baseline, run count, spread and limiter, and with proof the work ran without errors. A change within the noise is reverted. | You report, compare or act on a performance or eval number. | tuning-performance, design (NFRs), plan (perf checks), verify, evals | pstack Explain the Number, benchmark-checklist |
| 9 | **Run it or ask its owner** | When a question is a fact a short run can settle, run a throwaway spike and cite what it showed. When it is a product, risk or approval call, ask its owner. Never guess either kind. | An UNKNOWN or a fork in intent, discover, design or plan. | design 3-4, discover 3, plan 2 | pstack Prototype, Exhaust the Design Space; the bounded half of Never Block on the Human |
| 10 | **Shape before logic** | Name the data structure and where validation sits before writing logic: a state machine, a typed model, a table. A reshape must remove branches or invalid states. | Stateful or branching logic, a new module, or an if-chain that grows. | specify 2, design, plan 7 (bundle), designing-apis, reviewing-code, simplifying-code | pstack Model the Domain, Foundational Thinking, Boundary Discipline |
| 11 | **State lives in git** | Everything a later session needs is committed: the bundle, the progress note, the index. A resume reads it, redoes nothing committed, and changes only what differs. | You end, pause or resume a session, or hand work to a sub-agent or a lane. | build, parallel-lanes, every stage's index row | aidlc + pstack Make Operations Idempotent, Session pickup |
| 12 | **Encode the lesson** | A mistake seen twice gets a check, at the highest layer that works, proven on the past mistake. | A finding or a correction repeats. | review, feedback, operate | aidlc-feedback + pstack Encode Lessons in Structure |

Left out on purpose: "Separate before you share" (it lives in `parallel-lanes` and needs no steering name),
"Experience first" (the product owner's), and "Never block on the human" (number 9 is aidlc's bounded form).

---

## 4. Where the ADOPT and STRENGTHEN items land, ranked

Ranked by value to a team using aidlc: time saved, defects caught, and steps not missed. ★ marks the top 10.

### Rank 1. `debugging-failures` and `aidlc-build` step 8 (every story hits failures)

1. ★ **Competing causes, then the cheapest test that rules most of them out** (Bug fix `:8`). STRENGTHEN.
2. ★ **Revert a refuted attempt before the next one; ship only what the evidence supports** (Bug fix `:5`). STRENGTHEN.
3. ★ **Attack the premise at the second failed fix** (principle). ADOPT. Before attempt three, write the premise
   attempts one and two shared, and test it. The stop report names it. This makes aidlc's three-attempt limit
   useful instead of only stopping.
4. ★ **Fix the pattern, not the instance; a guard is a fix only for a legitimate state; propose the always-on
   signal that would have shown it** (Fix Root Causes). STRENGTHEN. The signal goes to `aidlc-feedback` as a
   lesson (layer 3, a measure).
5. Prove the mechanism with a run before planning the fix (Bug fix `:8`, Runtime forensics `:7`). STRENGTHEN.
6. For a regression, read the commits and review threads (Bug fix `:8`, `why`). STRENGTHEN.
7. First check that the failing check measures what you think (Prove It Works). STRENGTHEN, small.

Why first: these change the outcome of the most common hard moment in a build. They cut wasted attempts, and they
stop "might help" code from reaching review.

### Rank 2. `aidlc-review`, `reviewing-code`, the reviewer agents and the pull request description

1. ★ **Drift check before Merge** (Autopilot-full `:19`, Babysit `:8`). ADOPT. It catches the green pull request
   that breaks the default branch.
2. ★ **Block only for what you can show; a defect the base already has is a follow-up** (worker.md `:6`,
   Autopilot-full `:16`). STRENGTHEN. Fewer stalled merges, and less scope creep.
3. ★ **A dismissal cites its disproof, and the team keeps a list of known review noise with "do not skip"
   limits** (Babysit `:9`, `bugbot-triage.md`). STRENGTHEN and ADOPT. This saves engineer time on each pull
   request, and the list stays reviewable.
4. A "Reach" section in the description (Opening a PR `:7`). ADOPT.
5. Rejected options a reviewer would ask about (Opening a PR `:7`). STRENGTHEN.
6. A short description with long tables linked (Opening a PR `:7`, worker.md `:11`). STRENGTHEN.
7. Verify: a red check outside the diff is checked against the base; one re-run by the person (Babysit `:8`).
   STRENGTHEN.

### Rank 3. `aidlc-design`, `aidlc-discover`, `aidlc-plan` and the task bundle

1. ★ **Settle a fact by running a throwaway spike** (Prototype; `poteto-mode:21`). ADOPT. A new reference,
   `aidlc-design/references/spike.md`: no decision, no spike; a scratch folder outside the source; installed tools
   only; time-boxed; variants behind one switch for a new interaction; the observation is cited as FACT; the
   spike's code never moves into the build.
2. ★ **DONE WHEN as commands, with live and performance checks per slice; the baseline measured on the default
   branch first** (Multi-phase plan `:8`, Autonomous run `:5`). STRENGTHEN.
3. The bundle names the data shape the slice introduces (Feature `:12`, Model the Domain). STRENGTHEN.
4. ORDER says what must come first, what could run apart, what is shared, and why one branch if so (Feature
   `:7-11`). STRENGTHEN.
5. Discover traces history as a sixth direction (Investigation `:7`). STRENGTHEN.
6. A repeated edit across many files is proposed as a RECIPE (Build the Lever). STRENGTHEN.

Why third: fewer wrong designs, fewer judgement calls in delegate slices, and verification that is planned, not
improvised. It adds a little work at plan time.

### Rank 4. `tuning-performance`

1. ★ **Explain the number**: write the claim first; name the limiter; count errors; confirm the work ran inside the
   timed region; tune both sides the same way; alternate the runs (A, B, A, B) at least five times and report the
   median and range; give the share of the end-to-end path; call it inconclusive when the limiter is unknown
   (Explain the Number, `benchmark-checklist`). STRENGTHEN.
2. The remedies in order, cheapest first (Perf issue `:7-16`). STRENGTHEN.
3. Prove the harness can tell cases apart, then freeze it (Hillclimb `:8`). STRENGTHEN.
4. Measure a case that shows the complaint, or fix the reproduction first (Hillclimb `:7`). STRENGTHEN.
5. Reduce a profile to the one hot function or retainer chain (Runtime forensics `:6`). STRENGTHEN.

Why fourth: high value per use, but only on performance work. Wrong performance claims are common and costly.

### Rank 5. `simplifying-code`

1. ★ **Refactoring with a real pin, an equivalence script, and one-wave migration of internal callers with a
   rename sweep** (Refactoring `:7,11,12`). STRENGTHEN.
2. Commit order: deletions, then the reshape, then tidy-up (Refactoring `:10,14`). STRENGTHEN.
3. Name what got simpler, or revert (Refactoring `:13`). STRENGTHEN.
4. A shared-helper fix finds every caller; a caller outside MAY CHANGE is a stop (Feature `:12`). STRENGTHEN.

### Rank 6. `testing-in-browser` (and route S upgrades)

1. A visual baseline before a no-visual-change migration, an image diff, and the baseline treated as an assertion
   (Visual parity `:5-8`). ADOPT. It is just outside the top 10 because it applies to fewer stories. It is high
   value for framework and design-system upgrades.

### Rank 7. `aidlc-build` session handling and the progress note

1. A requested pause backs out to the last green commit and writes `RESUME AT` (Pause safely `:5,8`). STRENGTHEN.
2. A resumed slice matches checked steps with commits (Session pickup `:7`). STRENGTHEN.

### Rank 8. `using-aidlc`: the Principles section (section 3)

It is a steering vocabulary, not new behaviour. Its value grows with each item above that it names.

### Rank 9. `writing-tests`

1. The second imagined edit: change the internals, and the test must still pass. The expected value comes from the
   requirement, never from the code under test. Assert the error type callers branch on, not its message (Test
   Behavior). STRENGTHEN, small. This applies only to tests you write. Existing assertions stay.

### Rank 10. `evals/README.md` and a team's eval cases (`aidlc-feedback` step 3)

1. Prompts never reveal that they are a test (Eval `:7-10`). STRENGTHEN.
2. Read a sample of the failed runs yourself before trusting a grader (Eval `:23`). STRENGTHEN.

### Rank 11. `aidlc-operate` and `ops-diagnoser`

1. A cause is confirmed only with a paired capture, before and after (Trace forensics `:11`). STRENGTHEN, small.

### The top 10, in one list

| ★ | Concept | From | Verdict | Lands in |
|---|---|---|---|---|
| 1 | Drift check before Merge | Autopilot-full `:19`, Babysit `:8` | ADOPT | `aidlc-review` step 8 |
| 2 | Competing causes, cheapest test that rules most out | Bug fix `:8` | STRENGTHEN | `debugging-failures` (new step after Localize) |
| 3 | Revert a refuted attempt before the next | Bug fix `:5` | STRENGTHEN | `aidlc-build` step 8, `debugging-failures` step 5 |
| 4 | Test the shared premise after the second failed fix | principle Attack the Premise | ADOPT | `debugging-failures`, `aidlc-build` step 8 |
| 5 | Settle a fact by a throwaway spike | Prototype; `poteto-mode:21` | ADOPT | `aidlc-design` steps 3-4 and a new `references/spike.md`; discover step 3; plan step 2 |
| 6 | DONE WHEN as commands, with live and performance checks, baseline first | Multi-phase plan `:8`; Autonomous run `:5` | STRENGTHEN | `aidlc-plan` step 7, the task bundle, `aidlc-verify` step 2 |
| 7 | Block only for what you can show; base defects are follow-ups | worker.md `:6`; Autopilot-full `:16` | STRENGTHEN | `reviewing-code` Step 5, reviewer agents, `aidlc-review` step 4 |
| 8 | Explain the number | principle Explain the Number; `benchmark-checklist` | STRENGTHEN | `tuning-performance` steps 1 and 4 |
| 9 | Fix the pattern everywhere; legitimate-state test for guards; always-on signal | principle Fix Root Causes | STRENGTHEN | `debugging-failures` step 5 and Verification; `aidlc-feedback` |
| 10 | Dismiss with a disproof, and keep a known-noise list | Babysit `:9`; `bugbot-triage.md` | STRENGTHEN + ADOPT | `aidlc-review` step 4; `aidlc-feedback` step 4 (team `AGENTS.md`) |

Next in line: the refactoring pin, equivalence script and one-wave migration (`simplifying-code`), then the visual
baseline (`testing-in-browser`).

### Suggested packaging

- **One plan, "diagnosis and merge readiness"**: rank 1 and rank 2 items 1 to 3. They touch `debugging-failures`,
  `aidlc-build` step 8, `aidlc-review` steps 4 and 8, `reviewing-code` Step 5, the four reviewer agents and
  `aidlc-feedback` step 4. No gate changes. Each item tightens a step. Evals: one for a third attempt after two
  failures on one premise, one for a pull request whose base moved under a touched file.
- **One plan, "decide by evidence"**: the spike reference and DONE WHEN checks (rank 3 items 1 and 2), and
  Explain the Number (rank 4 item 1). It pairs with the structural review's "Drive the app" (its rank 4), because
  live checks need a way to drive the app.
- **One plan, "craft practices"**: ranks 5, 6, 7 and 9, plus the Principles section (rank 8), with the
  structural review's rank 6.

---

## 5. Conflicts with aidlc's fixed decisions: do not adopt

| # | pstack text | Why it conflicts | aidlc rule |
|---|---|---|---|
| 1 | The agent merges: `gh pr merge`, `origin pr merge`, armed `--auto` merge (`PB/shipping.md:8`; `PB/autopilot-full.md:8,17`) | The AI never approves or merges. | ADR 0023; `aidlc-review:53` |
| 2 | Force-push with lease, rebase and retarget by the agent (`PB/autopilot-full.md:8,12`; `PB/shipping.md:8`) | The person pushes. The AI holds no push credential. | `tiers-table.md:61`; `committing-changes:46,69` |
| 3 | The agent opens the pull request, ready (`PB/opening-a-pr.md:9`; every code playbook ends "Run Opening a PR") | The person pushes and opens the pull request. | `aidlc-build:44` |
| 4 | The owner's countersign is the approval under a grant (`PB/autopilot-full.md:20`) | An agent's verdict is evidence, never an approval. | ADR 0023; `aidlc-review:65` |
| 5 | "Never call a tool that shows a person a question"; "Do not park reversible work for the human or use AskQuestion" (`worker.md:7`; `PB/autonomous-run.md:9`; `principle-never-block-on-the-human`) | Ready, Design + plan, Merge and Release are people's decisions, before the fact. Intent and specify need the product owner's answers. | ADR 0026; `tiers-table.md:24-31` |
| 6 | "The bar in your kickoff is the whole bar. Add no check, gate, sign-off or review round above it" (`worker.md:4`) | Gates come from the stage skill, never from a brief. A brief may narrow work, never lift a gate. | AGENTS.md Boundaries |
| 7 | "Mid-run discoveries are yours: fix related bugs, broken skills, drift, in their own PR" (`PB/autonomous-run.md:9`) | Work outside MAY CHANGE is a stop or a new work item. Framework owners own the skills. | `aidlc-build:43,74`; `roles.md:10` |
| 8 | "Delete tests that only protect pre-refactor implementation details" (`principle-migrate-callers-then-delete-legacy-apis`); "Rewrite or delete the rest" (`principle-test-behavior-not-implementation`) | Never change an existing assertion. A deleted test lowers the Quality bar. Adopt the test checks only for new tests. | `aidlc-build:59-60`; `writing-tests:47` |
| 9 | "Intermediate breakage is acceptable when planned" (`principle-outcome-oriented-execution`) | Every slice starts and ends green. A build stops when a slice starts red. | `aidlc-plan:64`; `aidlc-build:35` |
| 10 | A `wip:` commit on a broken tree to pause (`PB/pause-safely.md:7`) | Every commit builds and passes, so bisect works. Back out to the last green commit instead. | `committing-changes:25,39,59` |
| 11 | `git worktree remove --force` and `rm -rf` the folder (`PB/worktree-cleanup.md:7`) | A lane never passes `--force`. A worktree may hold uncommitted work. | `parallel-lanes:171,277` |
| 12 | Posting replies and resolving review threads through `gh api` (`PB/babysit.md:9`; `bugbot-triage.md`, Decision rubric); "external actions (team chat, ticket updates) proceed without asking" (`poteto-mode:76`) | Posting to the pull request or the tracker asks the person first. | `aidlc-review:59`; ADR 0023 |
| 13 | A decision log kept out of git (`PB/hillclimb.md:9`; `show-me-your-work`) | The decision log and the performance ledger are committed and read at Merge. | ADR 0027; `tuning-performance:178` |
| 14 | "Hotfix the live code without reloading" (`PB/runtime-forensics.md:7`) | The AI has no production access. Local processes only. | `aidlc-operate:35,55` |
| 15 | Delegation to a sub-agent is "mandatory", with no skip (`PB/feature.md:12`) | MODE comes from the plan and the tier. Tier 3 is hands-on only. A Tier 1 build with a stated plan is not sent to a sub-agent lane. | `tiers-table.md:14`; ADR 0025 |
| 16 | "Port shared-primitive improvements to all consumers" (`PB/feature.md:12`) | A consumer outside MAY CHANGE, or another team's code, is a stop. Take it only with that limit. | `aidlc-build:106` |
| 17 | "`/loop` per component until the diff is zero" (`PB/visual-parity.md:8`); "A plateau is not a stop, keep going" (`PB/autonomous-run.md:11`) | Three attempts at the same failure, then stop and report. | `aidlc-build:42,73` |
| 18 | Prototype "CDN deps", installed in a scratch folder (`PB/prototype.md:9`) | No new dependency without asking, and never install a tool yourself. A spike uses only what is installed. A package to fetch asks first. | AGENTS.md Boundaries; `debugging-failures:289` |
| 19 | "Tell it to do the thing and skip the reason" (`PB/authoring-a-skill.md:10`) | aidlc explains why, not only what. | AGENTS.md Standards |
| 20 | Chat transcripts as the trail (`PB/session-pickup.md:5`; `PB/eval.md:22`) | Host-specific and private. State is in git. | `aidlc-build:102` |
| 21 | Host-only tools: `/loop`, `watch-pr`, cloud agents, Bugbot, `/deslop`, `control-ui`, `control-cli`, model slugs, `/setup-pstack` (`PB/autonomous-run.md:6`; `PB/babysit.md:6`; `poteto-mode:88-96`) | aidlc ships no code and stays host-neutral. It names "the repository's commands from AGENTS.md". | ADR 0024; AGENTS.md Standards |

A safe way to adopt any item above: copy the idea, not the verb. Where pstack says "the agent merges, pushes,
posts or decides", aidlc says "the AI drafts it, says so, and a person does it".

## 6. Credit

pstack is MIT (`LICENSE:1-3`, "Copyright (c) 2026 Lauren Tan"). Ideas need no notice. Where a landing keeps
pstack's wording, for example the remedy order in Perf issue or the questions of `benchmark-checklist`, add pstack's
MIT notice to `skills/NOTICE`, next to the existing third-party notice, and credit pstack in the ADR that adds the
change. Prefer aidlc's own short sentences, as the landings above are written.
