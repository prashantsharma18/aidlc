# pstack's principles in aidlc: where each one lands

Read-only research, 2026-11-22. aidlc at local `main` (2a54c23, aidlc 8.2.0, after Plans 27 to 29). pstack is the local
copy under `scratchpad/pstack-gh/tree/pstack/` (MIT, Lauren Tan). A pstack path is relative to `pstack/`; `PB/` means
`skills/poteto-mode/playbooks/`; `PM` means `skills/poteto-mode/SKILL.md`. An aidlc path is relative to the repository
root, and `PLAY/` means `skills/story-run/references/`. `file:N` is line N of the file as it is on disk (long lines are
not wrapped).

The earlier review (`docs/research/2026-11-22-pstack-review/2-playbooks-and-principles.md`, sections 2 and 3) was
written at 29a5b2a. Its verdicts mostly hold, but its line numbers moved (for example its `aidlc-build:42,73` for the
three attempts is now `skills/aidlc-build/SKILL.md:47,79`), and Plans 27 to 29 added text that now holds several
principles almost word for word: the playbooks (`PLAY/playbook-*.md`), the throughput checkpoint in `aidlc-plan`
step 5, and `lane-run`. Its section 3 proposed 12 aidlc-named principles; the owner has since chosen pstack's own
names and shape instead, so section 3 is superseded, and its grouping ideas survive only as citation points below.

Word headroom today (`wc -w`, as the tests count):

| File | Words | Limit (test) | Headroom |
|---|---|---|---|
| `skills/story-run/SKILL.md` | 2,298 | 2,300 (`scripts/test_connect_flow.py:549` RUN_LIMIT) | **2** |
| `skills/aidlc-plan/SKILL.md` | 3,497 | 3,500 (`scripts/test_references.py:234`) | **3** |
| `skills/aidlc-build/SKILL.md` | 4,394 | 4,400 (`scripts/test_references.py:295`) | **6** |
| `skills/lane-run/` SKILL.md + references (worker.md counts) | 3,879 | 3,900 (`scripts/test_parallel_pstack.py:216`) | **21** |
| `skills/lane-run/references/worker.md` alone | 256 | 300 (`scripts/test_parallel_pstack.py:212`) | 44 |
| `skills/aidlc-design/SKILL.md` | 2,567 | 2,600 (`scripts/test_references.py:183`) | 33 |
| `skills/aidlc-specify/SKILL.md` | 1,964 | 2,000 (`scripts/test_references.py:164`) | 36 |
| `skills/aidlc-start/SKILL.md` | 2,761 | 2,800 (`scripts/test_references.py:205`) | 39 |
| `skills/parallel-lanes/` SKILL.md + references | 2,996 | 3,300 (`scripts/test_parallel_pstack.py:217`) | 304 |

No limit: the playbooks, every practice, every agent, `using-aidlc`, and every stage's `references/*.md`
(`scripts/test_references.py:50-52` counts `SKILL.md` only). A backticked name in brackets, "(`principle-x`)", is one
word to `split()`, so a limited file can take a citation for one word. `aidlc-plan` can take two such citations and no
more (3,497 + 2 < 3,500); `story-run` can take none beyond what section 6 needs.

---

## Summary

"Verdict" says what citing the principle does to aidlc's existing text: **explains** (the rule is there; the name
gives the reason), **strengthens** (the leaf adds a check aidlc lacks), **repeats** (aidlc already says it, often
more strictly; the citation is only vocabulary). "Conflict?" is about the leaf's own words against an aidlc gate.

| # | Principle | Group | aidlc today | Verdict | Cite at (at most three) | Conflict? |
|---|---|---|---|---|---|---|
| 1 | `principle-laziness-protocol` | core | `PLAY/playbook-bug-fix.md:5-6,24`; `simplifying-code:39`; `reviewing-code:52-53` | explains (adds "one source of truth") | `PLAY/playbook-bug-fix.md:24`; `simplifying-code:23`; `reviewing-code:52` | no |
| 2 | `principle-foundational-thinking` | core | `PLAY/playbook-feature.md:16-17`; `aidlc-plan:64`; `aidlc-plan/references/route-g.md:5` | explains | `PLAY/playbook-feature.md:16`; `aidlc-plan/references/route-g.md:5` | small: "CI ... goes first" |
| 3 | `principle-redesign-from-first-principles` | core | `aidlc-design/references/amendment.md`; `aidlc-plan/references/revision.md`; `PLAY/playbook-refactoring.md:18-20` | explains at design and plan; conflicts in build | `aidlc-design/references/amendment.md:5`; `aidlc-plan/references/revision.md:5`; `PLAY/playbook-refactoring.md:18` | **yes**: "every reference"; redesign inside a build |
| 4 | `principle-attack-the-premise` | core | `aidlc-build:79` (stop after a different fix fails the same way); `debugging-failures:43`; `PLAY/playbook-bug-fix.md:17-19` | strengthens (new) | `debugging-failures:43`; `PLAY/playbook-bug-fix.md:25`; `lane-run:207` | **yes**: aidlc stops where pstack writes the next fix |
| 5 | `principle-subtract-before-you-add` | core | `PLAY/playbook-refactoring.md:16-17` (uses the name); `simplifying-code:16,30`; `PLAY/playbook-performance.md:19` | repeats | `PLAY/playbook-refactoring.md:16`; `simplifying-code:16` | small: "Simplify prompts" |
| 6 | `principle-minimize-reader-load` | core | `reviewing-code:68,106,346`; `simplifying-code:29`; `PLAY/playbook-refactoring.md:24` | repeats (adds the 30-second test) | `PLAY/playbook-refactoring.md:24`; `reviewing-code:68` | small: adapters vs test fakes |
| 7 | `principle-exhaust-the-design-space` | core | `aidlc-design:48` (two options, on paper); `PLAY/playbook-spike.md:17-18` | strengthens design; repeats spike | `PLAY/playbook-spike.md:17`; `aidlc-design:48` (1 word) | **yes**: who commits to the choice |
| 8 | `principle-build-the-lever` | core | `aidlc-plan:84` (RECIPE); `aidlc-build:44`; `aidlc-build/references/recipe-commit.md:5`; `PLAY/playbook-refactoring.md:12-13` | explains RECIPE; strengthens elsewhere | `aidlc-plan:84` (1 word); `PLAY/playbook-refactoring.md:12`; `aidlc-build/references/recipe-commit.md:5` | **yes**: first unit by hand; a file in the diff |
| 9 | `principle-model-the-domain` | architecture | `PLAY/playbook-feature.md:16-17`; `PLAY/playbook-refactoring.md:14-15`; `reviewing-code:57,100` | repeats | `PLAY/playbook-feature.md:16`; `PLAY/playbook-refactoring.md:14`; `reviewing-code:57` | no |
| 10 | `principle-boundary-discipline` | architecture | `designing-apis:97-99,390,407`; `securing-code:55,113` | repeats (adds pure core, thin shell) | `designing-apis:97`; `securing-code:113` | no |
| 11 | `principle-type-system-discipline` | architecture | `designing-apis:361-365,405`; `reviewing-code:70` | repeats (adds exhaustive variants, schema-derived types) | `designing-apis:361`; `reviewing-code:70` | small: names a skill aidlc lacks |
| 12 | `principle-make-operations-idempotent` | architecture | `designing-apis:165-170`; `stress-testing-decisions:26`; `lane-run:96`; `story-run:40-41` | explains the workflows; repeats for APIs | `designing-apis:165`; `lane-run:96` (1 word) | **yes**: "stale" leftovers vs another lane's worktree |
| 13 | `principle-migrate-callers-then-delete-legacy-apis` | architecture | `PLAY/playbook-refactoring.md:18-22` (the rule, for an internal API) | repeats | `PLAY/playbook-refactoring.md:18`; `migrating-safely:25` | **yes**: deletes and updates tests |
| 14 | `principle-separate-before-serializing-shared-state` | architecture | `aidlc-plan:66` (SHARED); `parallel-lanes:62-69`; `aidlc-plan/references/independent-slices.md:11-12` | repeats (stronger: git's lock) | `aidlc-plan:66` (1 word); `parallel-lanes:62` | no |
| 15 | `principle-prove-it-works` | verification | `aidlc-verify:29`; `aidlc-build:112`; `PLAY/playbook-feature.md:22-23`; `PLAY/playbook-bug-fix.md:27-28` | explains (adds "suspect the observation first") | `PLAY/playbook-feature.md:22`; `aidlc-verify:29`; `PLAY/playbook-refactoring.md:23` | **yes**: "commit it only when"; self-check vs non-author verdict |
| 16 | `principle-fix-root-causes` | verification | `debugging-failures:146-161,223-225`; `PLAY/playbook-bug-fix.md:24` | strengthens (legitimate-state test, always-on signal) | `debugging-failures:146`; `PLAY/playbook-bug-fix.md:24` | small: "every place" |
| 17 | `principle-sequence-verifiable-units` | verification | `aidlc-plan:64`; `aidlc-build:46`; `PLAY/playbook-feature.md:24`; `committing-changes:39` | repeats (stronger) | `PLAY/playbook-feature.md:24`; `committing-changes:39` | **yes**: a failing-test commit before the fix |
| 18 | `principle-test-behavior-not-implementation` | verification | `writing-tests:41-42`; `agents/reviewer-tests.md:25-26` | strengthens (second edit, expected value from the requirement, error type) | `writing-tests:41`; `agents/reviewer-tests.md:25` | **yes**: "Rewrite or delete the rest" |
| 19 | `principle-explain-the-number` | verification | `PLAY/playbook-performance.md:17-18` (uses the name); `tuning-performance:149-153` | repeats in the playbook; strengthens the practice | `PLAY/playbook-performance.md:17`; `tuning-performance:153` | small: names a skill aidlc lacks |
| 20 | `principle-guard-the-context-window` | delegation | `aidlc-plan:53`; `aidlc-discover:37`; `agents/explorer.md:18`; `aidlc-build:27`; `story-run:112` | repeats | `aidlc-discover:37`; `agents/explorer.md:18` | small: "Route bulk to subagents" |
| 21 | `principle-encode-lessons-in-structure` | meta | `aidlc-feedback:29-34` (uses the words) | repeats (stronger: proven on the past mistake) | `aidlc-feedback:29` | small: the AI proposes, the owner encodes |

Totals: 21 leaves, 47 citation points, none above three. Only five land in word-limited files, each as a one-word
bracket: `aidlc-plan:66` and `:84`, `aidlc-design:48`, `lane-run:96` and `:207`. `aidlc-build` and `story-run` get no
citation at all; they get the index read and the decision-log wording only (section 6). The refactoring playbook takes
seven citations, as pstack's own `PB/refactoring.md:8-14` does.

---

## Per principle

Each entry: (1) pstack's trigger and rule, and where pstack cites it; (2) aidlc's existing rule and the verdict; (3)
where to cite it, with the pointer; (4) any leaf wording that crosses an aidlc gate, with the note to put beside it.
Every principle is also listed in `README.md:222-254` and `docs/guide/08-principles.md:29-72`; those are not repeated.

The proposed note goes on its own line at the end of the leaf, after pstack's text, starting `**In aidlc.**`. It
never rewrites pstack's words.

### 1. Laziness Protocol (`principle-laziness-protocol`), core

1. **pstack.** When: "Refactoring, sizing a diff, or tempted to add abstractions, layers, or signal threading" (`PM:37`).
   Rule: "Bias toward deletion and the smallest change that solves the problem" (leaf description). The leaf adds
   "Consolidate decisions ... Put it behind one source of truth" (`skills/principle-laziness-protocol/SKILL.md:9`).
   Cited: `skills/figure-it-out/SKILL.md:30` ("A second arena over a settled design is over-engineering"),
   `PB/refactoring.md:10` ("The smallest change that reaches the target shape ships"), `PB/hillclimb.md:17`,
   `PB/feature.md:12` ("Laziness Protocol does not override it"), `skills/arena/SKILL.md:34`, and `PB/prototype.md:5`
   (the one playbook where it "inverts").
2. **aidlc today.** `PLAY/playbook-bug-fix.md:5-6`: "A change that "might help" is a guess, and it does not ship: the
   smallest change the evidence supports ships, nothing more." `PLAY/playbook-bug-fix.md:24`: "Make the smallest fix
   the evidence supports". `skills/simplifying-code/SKILL.md:39`: "No abstraction was added for a single use."
   `skills/reviewing-code/SKILL.md:52`: "**Could this be done in fewer lines?**". Verdict: **explains**; "one source of
   truth per decision" is new.
3. **Cite at.**
   - `PLAY/playbook-bug-fix.md:24`, step 5: "Make the smallest fix the evidence supports (`principle-laziness-protocol`), and fix every instance ...".
   - `skills/simplifying-code/SKILL.md:23`, step 3: "Choose the change that removes the most moving parts, as `principle-laziness-protocol` says:".
   - `skills/reviewing-code/SKILL.md:52`: "**Could this be done in fewer lines?** (`principle-laziness-protocol`)".
4. **Conflict.** None with a gate. Optional note, since "one source of truth" can sit outside the slice:
   "**In aidlc.** The source of truth is inside MAY CHANGE, or the change is a stop (`aidlc-build` Stop if)."

### 2. Foundational Thinking (`principle-foundational-thinking`), core

1. **pstack.** When: "Before writing logic: core types and data structures, scaffold-vs-feature sequencing, what
   concurrent actors share" (`PM:38`). Rule: "Get the data structures right so downstream code becomes obvious."
   Cited: `skills/figure-it-out/SKILL.md:27` ("Scaffold and verification come before features"),
   `PB/refactoring.md:9` (with redesign, "Name the target shape").
2. **aidlc today.** `PLAY/playbook-feature.md:16-17`: "Name the data shape first: the structure the slice adds,
   chosen before the logic." `skills/aidlc-plan/SKILL.md:64`: "The usual slices are: map (read-only); core change ...".
   `skills/aidlc-plan/references/route-g.md:5-7`: slice 0, "the first slice of each new repository", RECIPE holds the
   SCAFFOLD. The shared-state half is principle 14's (`aidlc-plan:66`). Verdict: **explains**.
3. **Cite at.**
   - `PLAY/playbook-feature.md:16`, step 2: "Name the data shape first (`principle-foundational-thinking`, `principle-model-the-domain`): ...".
   - `skills/aidlc-plan/references/route-g.md:5`: "Slice 0 (route G), the first slice of each new repository, is the scaffold every later slice builds on, as `principle-foundational-thinking` says, on branch ...".
   - Not in `aidlc-plan/SKILL.md`: its two spare words go to principles 8 and 14.
4. **Conflict.** Leaf `:13`: "Scaffold first. Whatever helps every later phase (CI, tests, shared types) goes first,
   after removing dead code." In aidlc a CI step or a tool is proposed to its owner (`skills/aidlc-feedback/SKILL.md:33-34`,
   "A check that needs a new tool, lint plugin, dependency or CI step is proposed to its owner and waits for the answer").
   Note: "**In aidlc.** A scaffold is a slice the approved plan names; a new tool or CI step is a person's dependency decision."

### 3. Redesign from First Principles (`principle-redesign-from-first-principles`), core

1. **pstack.** When: "Integrating a new requirement into an existing design" (`PM:39`). Rule: "Redesign as if it had
   been foundational from day one." Leaf `:13`: "Propagate the change through every reference: types, docs,
   examples, rationale sections". Cited: `PB/refactoring.md:9`, `skills/arena/SKILL.md:38` (fold grafts in by hand),
   `skills/no-comments/SKILL.md:22`, which bounds it: "guide intent only. Neither authorizes widening the fence".
2. **aidlc today.** `skills/aidlc-design/references/amendment.md:5-7` (a contract's next version, expand and contract);
   `skills/aidlc-plan/references/revision.md:5-7` (a revision "pinned to the new spec that covers only the change
   between the two versions"); `PLAY/playbook-refactoring.md:18-20`: "then search for the old name in strings, docs,
   configuration and tests" (the "every reference" half). Verdict: **explains** at design and plan; it **conflicts**
   inside a build.
3. **Cite at.**
   - `skills/aidlc-design/references/amendment.md:5`, step 2: "Draft the contract's next version as if the change had been there from the start (`principle-redesign-from-first-principles`), and the updated consumer tests."
   - `skills/aidlc-plan/references/revision.md:5`, Step 5: "... a bundle pinned to the new spec that covers only the change between the two versions, designed as `principle-redesign-from-first-principles` says."
   - `PLAY/playbook-refactoring.md:18`, step 4: "... then search for the old name in strings, docs, configuration and tests (`principle-redesign-from-first-principles`)."
4. **Conflict.** Leaf `:9`: "don't bolt it onto the existing design. Redesign ..." and `:13` "Propagate the change
   through every reference". In a build, `skills/aidlc-build/SKILL.md:75`: "The plan looks wrong ... Never improvise a
   new approach: it goes back to `aidlc-plan`", and `:74`: "A change needs a file outside MAY CHANGE ...: stop and
   report"; `:115`: "Never edit `AGENTS.md`, a published contract, or another team's files". Note, borrowing pstack's
   own bound: "**In aidlc.** It shapes design and plan. It never widens MAY CHANGE; in a build, a redesign is a stop for `aidlc-plan`."

### 4. Attack the Premise (`principle-attack-the-premise`), core

1. **pstack.** When: "Two or more fixes that share one premise have failed the same gate" (`PM:40`). Rule: "Write the
   premise down and test it directly before you write another fix that assumes it." Leaf `:15`: "Do not start the
   next fix before the premise is written down and tested." Cited: nowhere else in pstack (only `PM:40`, the README
   and the guide).
2. **aidlc today.** `skills/aidlc-build/SKILL.md:79` (Stop if): "The same failure has had three attempts, a different
   fix brought the same failure back, or a test that passed before now fails." `skills/debugging-failures/SKILL.md:43`:
   "If the same failure comes back after a different fix ... stop and report." `PLAY/playbook-bug-fix.md:17-19`:
   competing causes, each with the observation that rules it out. aidlc stops at exactly the principle's trigger
   (two different fixes, one failure), but nothing says what the stop report must contain. Verdict: **strengthens**.
3. **Cite at.**
   - `skills/debugging-failures/SKILL.md:43` (the "In this framework" callout): "... stop and report; first write the premise both fixes shared, and the observation that tests it, as `principle-attack-the-premise` says."
   - `PLAY/playbook-bug-fix.md:25`, step 5: "Before another attempt, back the last one out in full, and when two attempts failed the same way, write their shared premise and test it (`principle-attack-the-premise`)." (No "stop" in the sentence: `scripts/test_connect_flow.py:1033-1041` sends every playbook sentence with "stop" to POINTERS.)
   - `skills/lane-run/SKILL.md:207` (Stop if, two `fix(ci)` commits): "... write `stopped: <check> red after two fixes` in the build row, with the premise both fixes shared (`principle-attack-the-premise`) ...". One word in a near-limit file (lane-run, 21 left).
4. **Conflict.** Leaf `:15` assumes a next fix follows the premise test. In aidlc the second failed fix is already a
   stop. Note: "**In aidlc.** A second fix that fails the same way is a stop (`aidlc-build` Stop if): write the premise and its test in the stop's report; the premise test is a diagnosis, not an attempt."

### 5. Subtract Before You Add (`principle-subtract-before-you-add`), core

1. **pstack.** When: "Sequencing an addition, refactor, or rewrite" (`PM:41`). Rule: "Remove dead weight first, then
   build on the simpler base." Cited: `PB/refactoring.md:10`.
2. **aidlc today.** `PLAY/playbook-refactoring.md:16-17`: "Subtract before you add: delete dead code, fold wrappers
   that have one caller and remove orphan references, in a commit of their own, before the reshape." (pstack's name,
   already.) `skills/simplifying-code/SKILL.md:16`: "Before a change in tangled code: simplify first, in its own
   commits, then change the behaviour." `PLAY/playbook-performance.md:19`: the remedies start with "remove the work".
   Verdict: **repeats**.
3. **Cite at.**
   - `PLAY/playbook-refactoring.md:16`: "3. Subtract before you add (`principle-subtract-before-you-add`): ...".
   - `skills/simplifying-code/SKILL.md:16`: "... simplify first, in its own commits, then change the behaviour (`principle-subtract-before-you-add`)."
4. **Conflict.** Leaf `:17`: "Simplify prompts (remove redundant instructions, excessive templates)". The AI never
   edits `AGENTS.md` or a skill (`skills/aidlc-build/SKILL.md:115`; framework owners own the skills). A test is never
   dead weight: "a skipped or deleted test" lowers the Quality bar (`skills/aidlc-build/SKILL.md:65`). Note:
   "**In aidlc.** Remove only inside MAY CHANGE. A test is never dead weight, and `AGENTS.md` and the skills are their owners' to simplify."

### 6. Minimize Reader Load (`principle-minimize-reader-load`), core

1. **pstack.** When: "Reviewing or shaping code that's hard to trace" (`PM:42`). Rule: "Count layers and hidden state,
   collapse one-caller wrappers, shrink mutable scope." The test (leaf `:15`): "where does X come from?" and "what can
   change X?" in under 30 seconds. Cited: `PB/refactoring.md:13` ("The success measure is reduced reader load").
2. **aidlc today.** `skills/reviewing-code/SKILL.md:68`: "Count the concepts a reader must hold to follow the change";
   `:106`: "**Delete a pass-through wrapper**"; `:346`. `skills/simplifying-code/SKILL.md:29`: "inline a wrapper that
   adds nothing". `PLAY/playbook-refactoring.md:24`: "Name what got simpler: fewer layers to trace, or less state to
   hold." Verdict: **repeats**; the 30-second test and the state-scope ladder (returns over mutations, ...) are new.
3. **Cite at.**
   - `PLAY/playbook-refactoring.md:24`, step 6: "Name what got simpler (`principle-minimize-reader-load`): fewer layers to trace, or less state to hold."
   - `skills/reviewing-code/SKILL.md:68`: "... Count the concepts a reader must hold to follow the change, as `principle-minimize-reader-load` says."
4. **Conflict.** Leaf `:11`: "Collapse layers that only forward: wrappers with one caller, adapters with no second
   implementation". `skills/writing-tests/SKILL.md:45` wants external edges "behind your own adapter with a fake of it".
   Note: "**In aidlc.** A test's fake is an adapter's second implementation: keep the adapter. Inline only inside MAY CHANGE."

### 7. Exhaust the Design Space (`principle-exhaust-the-design-space`), core

1. **pstack.** When: "A novel interaction or architectural decision with no precedent" (`PM:45`). Rule: "Build 2-3
   competing prototypes and compare side by side before committing." Leaf `:9`: "It also applies to product design
   decisions where user experience depends on feel, not logic." Cited: `PB/prototype.md:10` ("build them behind one
   switcher ... This is the exhaust-the-design-space principle skill made cheap").
2. **aidlc today.** `skills/aidlc-design/SKILL.md:48`: "at least two real options (including the cheapest
   workaround)", on paper; `:49` sends an UNKNOWN a short run can settle to the spike playbook.
   `PLAY/playbook-spike.md:17-18`: "for a new screen with no example in the product, two or three variants behind one
   switch, each with a screenshot". Verdict: **strengthens** design step 3 for a decision with no precedent;
   **repeats** the spike.
3. **Cite at.**
   - `PLAY/playbook-spike.md:17`, step 5: "... two or three variants behind one switch, each with a screenshot (`principle-exhaust-the-design-space`)."
   - `skills/aidlc-design/SKILL.md:48`, step 3: "... at least two real options (including the cheapest workaround) (`principle-exhaust-the-design-space`)". One word (design, 33 left).
4. **Conflict.** "before committing" and "product design decisions" read as the AI choosing. In aidlc the decider
   chooses: `PLAY/playbook-spike.md:22-23` ("A choice between screen variants is the product owner's"), and the tech
   lead or architect approves the design (`aidlc-design` Gate). A prototype is a spike: scratch folder, installed
   tools only, time-boxed, never committed (`PLAY/playbook-spike.md:12-16`). Note: "**In aidlc.** Each prototype is a spike (`playbook-spike.md`); you recommend, and the decider chooses."

### 8. Build the Lever (`principle-build-the-lever`), core

1. **pstack.** When: "Any non-trivial work" (`PM:46`). Rule: "Build the tool that does or proves it (codemod, script,
   generator), not by hand. The tool is the artifact a reviewer reruns." Leaf `:11`: "Do the first unit by hand, then
   build the tool and prove it by rerunning it on that unit"; `:13`: "No script, codemod, generator, or delegate skill
   in the diff means you didn't apply it. Commit it when the work outlives the session." Cited:
   `PB/worktree-cleanup.md:3`, `PB/hillclimb.md:8` ("Build the measurement harness, prove its sensitivity, then freeze
   it"), `docs/guide/06-verify-and-ship.md:75`.
2. **aidlc today.** RECIPE, `skills/aidlc-plan/SKILL.md:84`: "fill RECIPE only for a deterministic tool ... as its own
   slice before any hand change"; `skills/aidlc-build/SKILL.md:44`, step 5: "On a clean tree, run exactly the approved
   command and change nothing by hand"; `skills/aidlc-build/references/recipe-commit.md:5-12` reruns the tool in a
   worktree and diffs (the rerunnable artifact). `PLAY/playbook-refactoring.md:12-13`: "a script that runs the old and
   the new code on the same inputs and compares the outputs". Verdict: **explains** RECIPE and the recipe check;
   **strengthens** the "script that proves it" elsewhere.
3. **Cite at.**
   - `skills/aidlc-plan/SKILL.md:84`: "- fill RECIPE (`principle-build-the-lever`) only for a deterministic tool ...". One word (plan: 3 left, and principle 14 takes one more).
   - `PLAY/playbook-refactoring.md:12`, step 1: "... or a script that runs the old and the new code on the same inputs and compares the outputs (`principle-build-the-lever`)."
   - `skills/aidlc-build/references/recipe-commit.md:5`: "Then run the recipe check, which proves the tool by rerunning it (`principle-build-the-lever`), with git, from the repository root ...".
4. **Conflict.** Three. (a) Leaf `:11` "Do the first unit by hand, then build the tool" against `aidlc-build:44`
   ("change nothing by hand") and `aidlc-plan:84` ("before any hand change"). (b) Leaf `:13` "in the diff ... Commit it"
   against MAY CHANGE (`aidlc-build:74`) and the dependency rule: a recipe's "tool and its version are a dependency
   decision for the person" (`aidlc-plan:84`). (c) The description's "a skill your subagents follow": aidlc's
   delegates read the stage skill and `worker.md`, which framework owners write. Note: "**In aidlc.** The hand-done unit is a trial in a scratch folder; the recipe commit still comes first. A lever enters the diff only on a path MAY CHANGE lists, with installed tools; otherwise its output goes in the evidence file."

### 9. Model the Domain (`principle-model-the-domain`), architecture

1. **pstack.** When: "Writing stateful logic, or code that branches a lot or repeats a shape assumption across files"
   (`PM:50`). Rule: "Encode the domain in a structure (state machine, typed model, table or registry, reducer,
   boundary, the right collection) instead of scattered conditionals." Cited: `PB/refactoring.md:8` ("Name the
   structure the code is missing per principle-model-the-domain"), `PB/feature.md:12`.
2. **aidlc today.** `PLAY/playbook-feature.md:16-17`: "A state machine, not scattered booleans; a table, not a chain of
   branches; a typed model, not the same assumption about a shape in many files." `PLAY/playbook-refactoring.md:14-15`:
   "Name the structure the code is missing ... The new shape removes branches or invalid states; it does not add a
   layer." `skills/reviewing-code/SKILL.md:57`: "They point to a missing model or dispatcher"; `:100`. Verdict:
   **repeats** (the playbooks were adapted from the pstack lines that cite it).
3. **Cite at.**
   - `PLAY/playbook-feature.md:16` (shared with principle 2, above).
   - `PLAY/playbook-refactoring.md:14`, step 2: "Name the structure the code is missing (`principle-model-the-domain`) ...".
   - `skills/reviewing-code/SKILL.md:57`: "... They point to a missing model or dispatcher (`principle-model-the-domain`)."
4. **Conflict.** None.

### 10. Boundary Discipline (`principle-boundary-discipline`), architecture

1. **pstack.** When: "Wiring validation, error handling, or framework adapters" (`PM:51`). Rule: "Guards at system
   boundaries, trust internal types, keep business logic pure." Cited: `skills/typescript-best-practices/SKILL.md:25`,
   `skills/typescript-best-practices/references/patterns.md:3,276`.
2. **aidlc today.** `skills/designing-apis/SKILL.md:97-99`: "### 3. Validate at Boundaries ... Trust internal code.
   Validate at the system edges"; `:390` (red flag: validation spread through internal code); `:407`.
   `skills/securing-code/SKILL.md:113`: "code further in uses only the parsed, typed value." Verdict: **repeats**; the
   pure core with a thin shell, and the two tests (leaf `:11`), are new.
3. **Cite at.**
   - `skills/designing-apis/SKILL.md:99`: "Trust internal code. Validate at the system edges, where external input comes in, as `principle-boundary-discipline` says:".
   - `skills/securing-code/SKILL.md:113`: "... code further in uses only the parsed, typed value (`principle-boundary-discipline`)."
4. **Conflict.** None with a gate. Optional note: "**In aidlc.** A model's or a tool's output is a boundary too (`securing-code`), and a change to the public surface is a contract change (`aidlc-design`)."

### 11. Type System Discipline (`principle-type-system-discipline`), architecture

1. **pstack.** When: "Designing types or a signature in any typed language" (`PM:52`). Rule: "Make illegal states
   unrepresentable, brand primitives, parse external data at boundaries." Cited:
   `skills/typescript-best-practices/SKILL.md:10`, `skills/typescript-best-practices/references/patterns.md:3`.
2. **aidlc today.** `skills/designing-apis/SKILL.md:361-365` ("### Use Branded Types for IDs"); `:405` ("typed input
   and output schemas"); `skills/reviewing-code/SKILL.md:70`: "**Are type boundaries explicit?**". Verdict:
   **repeats**; exhaustive variants and types derived from the schema are new.
3. **Cite at.**
   - `skills/designing-apis/SKILL.md:361`: "### Use Branded Types for IDs" gains, under it: "Brand IDs, parse at the boundary and derive types from the schema, as `principle-type-system-discipline` says."
   - `skills/reviewing-code/SKILL.md:70`: "**Are type boundaries explicit?** (`principle-type-system-discipline`) ...".
4. **Conflict.** Leaf `:15`: "For TypeScript syntax, see the **typescript-best-practices** skill." aidlc has no such
   skill, so the pointer dangles (the validator only checks `assets/`, `references/` and `scripts/` paths,
   `scripts/validate.py:54`). Note: "**In aidlc.** There is no `typescript-best-practices`: see `designing-apis`. A schema-to-type generator not installed is a new dependency."

### 12. Make Operations Idempotent (`principle-make-operations-idempotent`), architecture

1. **pstack.** When: "Designing commands, lifecycle steps, or loops that run amid crashes and retries" (`PM:53`).
   Rule: "Converge to the same end state." Leaf `:11`: "Derive each step from the state that exists"; `:13`:
   "Anything a run leaves behind (a lock, a temporary file, a half-written record, a claimed job) must be recognizable
   as stale by the next run". Cited: nowhere else in pstack.
2. **aidlc today.** `skills/designing-apis/SKILL.md:165-170` ("### 6. Honouring an Idempotency Key"; "Derive the key
   from the intent, not the attempt"); `skills/stress-testing-decisions/SKILL.md:26` (partial failure, retry,
   duplicate). The workflows are built on it: `skills/story-run/SKILL.md:40-41`, "the trail in git is the state, never
   the chat"; `skills/lane-run/SKILL.md:96`, "In the worktree, read the row's state on its branch again". Verdict:
   **explains** the workflows; **repeats** for APIs.
3. **Cite at.**
   - `skills/designing-apis/SKILL.md:165`: under the heading, "An endpoint a client retries converges to one result, as `principle-make-operations-idempotent` says."
   - `skills/lane-run/SKILL.md:96`, step 4: "In the worktree, read the row's state on its branch again (`principle-make-operations-idempotent`)." One word (lane-run, 21 left).
4. **Conflict.** Leaf `:13` invites the next run to judge a leftover stale. A lane never does that to another lane's
   claim: `skills/lane-run/SKILL.md:95` "never remove or work in a worktree you did not create", and the Common excuse
   at `:213`, "its lane looks idle; I will take it over". Note: "**In aidlc.** A lane never judges another lane's worktree stale: git's lock stands and a person decides (`lane-run`)."

### 13. Migrate Callers Then Delete Legacy APIs (`principle-migrate-callers-then-delete-legacy-apis`), architecture

1. **pstack.** When: "Introducing a new internal API while old callers exist" (`PM:54`). Rule: "Migrate and delete in
   one wave." Leaf `:9`: "Update tests to assert the new contract, and delete tests that only protect pre-refactor
   implementation details"; `:13`: "The project can absorb coordinated breaking changes". Cited: `PB/refactoring.md:11`.
2. **aidlc today.** `PLAY/playbook-refactoring.md:18-22`: "For an internal API with no users outside the repository,
   move every caller and delete the old one in the same slice ... A published API is a contract: changing it is a stop
   too". `skills/migrating-safely` covers external consumers. Verdict: **repeats**.
3. **Cite at.**
   - `PLAY/playbook-refactoring.md:18`, step 4: "For an internal API with no users outside the repository, move every caller and delete the old one in the same slice (`principle-migrate-callers-then-delete-legacy-apis`); ...".
   - `skills/migrating-safely/SKILL.md:25`, When to Use: "- Replacing an old system, API, or library with a new one (an internal API with no outside users follows `principle-migrate-callers-then-delete-legacy-apis` and the refactoring playbook)".
4. **Conflict.** Leaf `:9` against `skills/aidlc-build/SKILL.md:64` ("A test can only pass by changing an existing
   assertion. Never change it"), `:65` ("a skipped or deleted test" lowers the bar), and
   `PLAY/playbook-refactoring.md:28` ("no test deleted and no assertion changed"). Note: "**In aidlc.** A test changes only through AMENDED ASSERTIONS, by the criterion's owner; a test pinned to old internals is reported, never deleted. A published API is a contract (`migrating-safely`)."

### 14. Separate Before Serializing Shared State (`principle-separate-before-serializing-shared-state`), architecture

1. **pstack.** When: "Concurrent actors might write the same file, branch, key, or object" (`PM:55`). Rule: "Eliminate
   the sharing first." Leaf `:11`: "Instructions are not concurrency control". Cited: `skills/figure-it-out/SKILL.md:31`,
   `PB/visual-parity.md:7`, `PB/feature.md:10`, `skills/arena/SKILL.md:18`.
2. **aidlc today.** `skills/aidlc-plan/SKILL.md:66`: "SHARED, what two slices would both write, split first and run one
   after another only for a real invariant" (ADR 0030, adapted from pstack, `skills/NOTICE:30`).
   `skills/parallel-lanes/SKILL.md:62-69` (the clash table); `skills/aidlc-plan/references/independent-slices.md:11-12`
   ("so sibling pull requests never edit the same file"); git's worktree lock in `lane-run` step 3. Verdict:
   **repeats** (stronger: git's lock is the structural serialization).
3. **Cite at.**
   - `skills/aidlc-plan/SKILL.md:66`: "SHARED (`principle-separate-before-serializing-shared-state`), what two slices would both write, ...". One word (plan's last spare word).
   - `skills/parallel-lanes/SKILL.md:62`: "A ready row is held back, not dropped, when it clashes (`principle-separate-before-serializing-shared-state`):".
4. **Conflict.** None.

### 15. Prove It Works (`principle-prove-it-works`), verification

1. **pstack.** When: "After a task, before declaring done" (`PM:59`). Rule: "Verify against the real artifact, not a
   proxy or 'it compiles'." Leaf `:9`: "When a check fails, suspect the observation method before the system"; `:11`:
   "Keep its output where the human can see it, and commit it only when the trail must be auditable later." Cited:
   `skills/figure-it-out/SKILL.md:19`, `PB/session-pickup.md:9`, `PB/worktree-cleanup.md:4`, `PB/refactoring.md:12`,
   `PB/hillclimb.md:5`, `skills/arena/SKILL.md:44`, `skills/poteto-help/SKILL.md:147`,
   `skills/poteto-help/references/prompting.md:50`, `docs/guide/06-verify-and-ship.md:3`.
2. **aidlc today.** `skills/aidlc-verify/SKILL.md:29`: "Read the trusted run's results ... Never use your memory of
   earlier runs." `skills/aidlc-build/SKILL.md:112`: "A verdict that the change is done or passes counts only from
   someone who did not write it". `PLAY/playbook-feature.md:22-23`: "Prove it on the surface users reach". Verdict:
   **explains**; "suspect the observation first" is new.
3. **Cite at.**
   - `PLAY/playbook-feature.md:22`, step 5: "Prove it on the surface users reach (`principle-prove-it-works`): ...".
   - `skills/aidlc-verify/SKILL.md:29`, step 1: "Read the trusted run's results (`principle-prove-it-works`): the CI run on the pull request."
   - `PLAY/playbook-refactoring.md:23`, step 5: "Show that the new code is equivalent (`principle-prove-it-works`): ...".
4. **Conflict.** (a) Leaf `:11` "commit it only when the trail must be auditable later": in aidlc the trail always is;
   the evidence file is committed (`skills/aidlc-build/SKILL.md:48`, step 9) and the Merge reads it (ADR 0027). (b)
   Leaf `:9` "Verify every output" can read as self-certification; `aidlc-build:112` makes the author's check evidence,
   never the verdict. (c) "run the feature" in production is a person's (`aidlc-operate`). Note: "**In aidlc.** Your check is evidence, kept in the committed evidence file; the verdict comes from someone who did not write the change, and production is a person's."

### 16. Fix Root Causes (`principle-fix-root-causes`), verification

1. **pstack.** When: "Debugging" (`PM:60`). Rule: "Trace each symptom back to the first place the system went wrong
   and fix it there. A guard is a fix only when the state it handles is legitimate." Leaf `:13`: "Fix the pattern, not
   the instance. Find every place with the same fault."; `:14`: "propose the cheap, always-on signal". Cited:
   `skills/no-comments/SKILL.md:22` ("guide intent only").
2. **aidlc today.** `skills/debugging-failures/SKILL.md:146-161` ("### Step 5: Fix the Root Cause ... Keep asking 'Why
   does this happen?'"); `:223-225` ("## Fallbacks Are Behaviour ... Never add one to make a failing check pass");
   `PLAY/playbook-bug-fix.md:24`: "fix every instance of the same pattern inside MAY CHANGE; one outside is a stop".
   Verdict: **strengthens**: the legitimate-state test and the always-on signal are new.
3. **Cite at.**
   - `skills/debugging-failures/SKILL.md:148`: "Fix the underlying issue, not the symptom, as `principle-fix-root-causes` says: a guard is a fix only for a state that is legitimate."
   - `PLAY/playbook-bug-fix.md:24`, step 5: "... and fix every instance of the same pattern inside MAY CHANGE (`principle-fix-root-causes`); ...".
4. **Conflict.** Small. "every place" already carries aidlc's bound in the playbook. The signal is proposed, which
   fits `aidlc-feedback` layer 3. Note: "**In aidlc.** Every place inside MAY CHANGE; one outside is a stop. The signal is a proposal for its owner (`aidlc-feedback`)."

### 17. Sequence Work into Verifiable Units (`principle-sequence-verifiable-units`), verification

1. **pstack.** When: "Multi-step work (sweeps, migrations, runs of similar edits) and how you stack commits and PRs"
   (`PM:61`). Rule: "Break work into small units that each end in a check, verify each before the next, and order
   delivery so the sequence proves itself." Leaf `:13`: "Deliver in the order that proves the work: the failing test
   first, then the fix. ... Each commit lands on its own." Cited: `skills/figure-it-out/SKILL.md:38`,
   `PB/autonomous-run.md:8`, `PB/multi-phase-plan.md:7`, `PB/bug-fix.md:12` ("the canonical ... the failing test first
   and the fix on top"), `PB/perf-issue.md:18`, `PB/refactoring.md:14`, `PB/hillclimb.md:16`, `PB/feature.md:15`.
2. **aidlc today.** `skills/aidlc-plan/SKILL.md:64`: "Every slice starts and ends with the repository's tests green";
   `skills/aidlc-build/SKILL.md:46`: "commit each green step"; `PLAY/playbook-feature.md:24`: "Commit small ordered
   steps, each green."; `skills/committing-changes/SKILL.md:39`: "Every commit on the branch builds and passes its
   tests, so bisecting works". Verdict: **repeats** (stronger).
3. **Cite at.**
   - `PLAY/playbook-feature.md:24`, step 6: "Commit small ordered steps, each green (`principle-sequence-verifiable-units`)."
   - `skills/committing-changes/SKILL.md:39`: "... so bisecting works (`principle-sequence-verifiable-units`), except an approved recipe commit ...".
4. **Conflict.** Leaf `:13` puts a red commit (the failing test) before the fix. aidlc forbids it:
   `committing-changes:39`, and `PLAY/playbook-bug-fix.md:21-23`: "Record its failing run in the progress note before
   you write the fix; the test commits with the fix, because every commit passes". Note: "**In aidlc.** Every commit passes: the failing run is recorded in the progress note, and the test commits with the fix."

### 18. Test Behavior, Not Implementation (`principle-test-behavior-not-implementation`), verification

1. **pstack.** When: "Writing, changing, or keeping a test" (`PM:62`). Rule: "Assert what the code's users can observe,
   so the test fails when that behavior breaks and keeps passing when only the internals change." Leaf `:16`: "Keep a
   test that catches the first edit and survives the second. Rewrite or delete the rest." Cited: nowhere else.
2. **aidlc today.** `skills/writing-tests/SKILL.md:41`: "**Wrong code makes it fail.**" (the first edit); `:42`: "**It
   checks behaviour a caller sees:** ... Not private methods, call order or internal variables."
   `agents/reviewer-tests.md:25-26` ask the first edit and "what a caller sees". Missing: the second edit, an expected
   value derived from the requirement (not computed by the code), and "Assert the error type that callers branch on,
   not the message". Verdict: **strengthens**.
3. **Cite at.**
   - `skills/writing-tests/SKILL.md:41`, Checks: "- **Wrong code makes it fail; new internals do not.** ... (`principle-test-behavior-not-implementation`)". The wording change is the strengthening; the citation is one bracket.
   - `agents/reviewer-tests.md:25`: "For each test, ask whether it would fail if the code were wrong, and still pass if only the internals changed (`principle-test-behavior-not-implementation`) ...".
4. **Conflict.** Leaf `:16` "Rewrite or delete the rest" against `skills/writing-tests/SKILL.md:37` ("never touch an
   existing assertion"), `:51`, and `skills/aidlc-build/SKILL.md:64-65`. Note: "**In aidlc.** It shapes the tests you write. An existing test that fails the two edits is a finding for its owner, never rewritten or deleted."

### 19. Explain the Number (`principle-explain-the-number`), verification

1. **pstack.** When: "Before you measure, and before you trust, report, or act on a number you measured" (`PM:63`).
   Rule: "Find what limits it, and rule out that it measured something other than the work you think." Leaf `:14`:
   "For a performance number, run the [benchmark-checklist](../benchmark-checklist/SKILL.md) skill." Cited:
   `docs/guide/06-verify-and-ship.md:49`.
2. **aidlc today.** `PLAY/playbook-performance.md:17-18`: "Explain the number before you trust it: what limits it ...,
   how much it moves over repeated runs, and that it measured the work you think it did." (the name, already).
   `skills/tuning-performance/SKILL.md:149-153` (same command, same conditions; "Beat the noise, not just the mean").
   The practice has no limiter, no error count and no "did the work run". Verdict: **repeats** in the playbook;
   **strengthens** the practice.
3. **Cite at.**
   - `PLAY/playbook-performance.md:17`, step 3: "Explain the number before you trust it (`principle-explain-the-number`): ...".
   - `skills/tuning-performance/SKILL.md:153`: "**Beat the noise, not just the mean.** ... Then name what limits the number and rule out that it measured something else, as `principle-explain-the-number` says."
4. **Conflict.** Small: the leaf links a skill aidlc lacks, by a relative path the validator does not check. Note:
   "**In aidlc.** There is no `benchmark-checklist`: see `tuning-performance`. A profiler not installed is a new dependency."

### 20. Guard the Context Window (`principle-guard-the-context-window`), delegation

1. **pstack.** When: "Context fills up: large outputs, long files, repeated reads, fan-out planning" (`PM:67`). Rule:
   "Route bulk to subagents, keep summaries in the main thread." (The leaf body holds one bullet, "Size phases and cap
   scope"; the earlier review checked it matches upstream.) Cited: `PB/runtime-forensics.md:6`,
   `PB/trace-forensics.md:7`, `PB/worktree-cleanup.md:5`.
2. **aidlc today.** `skills/aidlc-plan/SKILL.md:53`: "Send heavy reading to the `explorer` agent with one precise
   question"; `skills/aidlc-discover/SKILL.md:37`; `agents/explorer.md:18`: "Then the findings, under 60 lines.";
   `skills/aidlc-build/SKILL.md:27` (a fresh session per slice); `skills/story-run/SKILL.md:112` (stop when the session
   has grown long). Verdict: **repeats**.
3. **Cite at.**
   - `skills/aidlc-discover/SKILL.md:37`, step 3: "... Send heavy reading to the `explorer` agent (`principle-guard-the-context-window`) ...".
   - `agents/explorer.md:18`: "First line: what you searched and what you excluded. Then the findings, under 60 lines, so the caller's context stays small (`principle-guard-the-context-window`)."
4. **Conflict.** Small. "Route bulk to subagents" fits reading. A build is delegated only as the bundle's MODE and
   the tier allow (Tier 3 is hands-on, `aidlc-build:41`). Note: "**In aidlc.** Sub-agents read freely; a build goes to a sub-agent only as the bundle's MODE allows."

### 21. Encode Lessons in Structure (`principle-encode-lessons-in-structure`), meta

1. **pstack.** When: "You catch yourself writing the same instruction a second time" (`PM:72`). Rule: "Encode it as a
   lint, metadata flag, runtime check, or script instead of more text." Leaf `:11`: "**Corollary:** If the fix is
   structural, only use the structural fix. The instruction is the symptom." Cited: `skills/figure-it-out/SKILL.md:50`,
   `skills/show-me-your-work/SKILL.md:53`.
2. **aidlc today.** `skills/aidlc-feedback/SKILL.md:29-34`: "Encode each lesson in structure, in the team's project ...
   a rule nobody can break beats a rule somebody must remember. A mistake that repeated ... always gets a check above
   layer 4", and `:42-46`, proven on the real past mistake. Verdict: **repeats** (stronger).
3. **Cite at.**
   - `skills/aidlc-feedback/SKILL.md:29`, step 2: "Encode each lesson in structure (`principle-encode-lessons-in-structure`), in the team's project."
4. **Conflict.** Small. The AI proposes; the owner encodes (`aidlc-feedback:33-34`; ADR 0024: aidlc ships no checks).
   `aidlc-feedback:49` also adds each rule to the "Rules and what enforces them" table in `AGENTS.md`, which is a
   record of the check, not the "more text" the corollary rejects. Note: "**In aidlc.** You propose the check to its owner, proven on the past mistake (`aidlc-feedback`)."

---

## 5. The index, drafted

A new `## Principles` section in `skills/using-aidlc/SKILL.md`, before `## Rules` (no word limit). The entries keep
pstack's words from `PM:37-72`, in `PM`'s order, with each leaf's name given in full (pstack derives most names from
the title, `PM:33`; giving them removes that rule and makes the index testable).

```markdown
## Principles

Twenty-one short rules from pstack, one leaf each. `story-run`, `worker.md` and `aidlc-start` read this index at the
start of a task. Read a leaf in full before you apply its principle: `../principle-<name>/SKILL.md` from this skill's
folder. Name each principle that shaped a choice, and the choice it changed, in the decision log's why; cite only a
leaf you read in this session. A principle explains a choice; it never permits one. Where a leaf's words differ from
a stage's gate, the gate holds, and the leaf's "In aidlc" line says where.

**Core**

- **Laziness Protocol** (`principle-laziness-protocol`). Refactoring, sizing a diff, or tempted to add abstractions, layers, or signal threading. Bias to deletion and the smallest change that solves the problem.
- **Foundational Thinking** (`principle-foundational-thinking`). Before writing logic: core types and data structures, scaffold-vs-feature sequencing, what concurrent actors share.
- **Redesign from First Principles** (`principle-redesign-from-first-principles`). Integrating a new requirement into an existing design. Redesign as if it had been foundational from day one.
- **Attack the Premise** (`principle-attack-the-premise`). Two or more fixes that share one premise have failed the same gate. Write the premise down and test it directly before you write another fix that assumes it.
- **Subtract Before You Add** (`principle-subtract-before-you-add`). Sequencing an addition, refactor, or rewrite. Remove dead weight first, then build on the simpler base.
- **Minimize Reader Load** (`principle-minimize-reader-load`). Reviewing or shaping code that's hard to trace. Count layers and hidden state, collapse one-caller wrappers, shrink mutable scope.
- **Exhaust the Design Space** (`principle-exhaust-the-design-space`). A novel interaction or architectural decision with no precedent. Build 2-3 competing prototypes and compare before committing.
- **Build the Lever** (`principle-build-the-lever`). Any non-trivial work. Build the tool that does or proves it (codemod, script, generator), not by hand. The tool is the artifact a reviewer reruns.

**Architecture**

- **Model the Domain** (`principle-model-the-domain`). Writing stateful logic, or code that branches a lot or repeats a shape assumption across files. Encode the domain in a structure (state machine, typed model, table or registry, reducer, boundary, the right collection) instead of scattered conditionals.
- **Boundary Discipline** (`principle-boundary-discipline`). Wiring validation, error handling, or framework adapters. Guards at system boundaries, trust internal types, keep business logic pure.
- **Type System Discipline** (`principle-type-system-discipline`). Designing types or a signature in any typed language. Make illegal states unrepresentable, brand primitives, parse external data at boundaries.
- **Make Operations Idempotent** (`principle-make-operations-idempotent`). Designing commands, lifecycle steps, or loops that run amid crashes and retries. Converge to the same end state.
- **Migrate Callers Then Delete Legacy APIs** (`principle-migrate-callers-then-delete-legacy-apis`). Introducing a new internal API while old callers exist. Migrate and delete in one wave.
- **Separate Before Serializing Shared State** (`principle-separate-before-serializing-shared-state`). Concurrent actors might write the same file, branch, key, or object. Eliminate the sharing first.

**Verification**

- **Prove It Works** (`principle-prove-it-works`). After a task, before declaring done. Verify against the real artifact, not a proxy or "it compiles".
- **Fix Root Causes** (`principle-fix-root-causes`). Debugging. Trace each symptom back to the first place the system went wrong and fix it there. A guard is a fix only when the state it handles is legitimate.
- **Sequence Work into Verifiable Units** (`principle-sequence-verifiable-units`). Multi-step work (sweeps, migrations, runs of similar edits) and how you stack commits and PRs. Break work into small units that each end in a check, verify each before the next, and order delivery so the sequence proves itself.
- **Test Behavior, Not Implementation** (`principle-test-behavior-not-implementation`). Writing, changing, or keeping a test. Assert what the code's users can observe, so the test fails when that behavior breaks and keeps passing when only the internals change.
- **Explain the Number** (`principle-explain-the-number`). Apply before you measure, and before you trust, report, or act on a number you measured (a speedup, a regression, a throughput, a latency, or an eval result). Find what limits it, and rule out that it measured something other than the work you think.

**Delegation**

- **Guard the Context Window** (`principle-guard-the-context-window`). Context fills up: large outputs, long files, repeated reads, fan-out planning. Route bulk to subagents, keep summaries in the main thread.

**Meta**

- **Encode Lessons in Structure** (`principle-encode-lessons-in-structure`). You catch yourself writing the same instruction a second time. Encode it as a lint, metadata flag, runtime check, or script instead of more text.

**Left out on purpose**

- **Outcome-Oriented Execution.** It accepts planned intermediate breakage; in aidlc every slice starts and ends green (`aidlc-plan` step 5), and a build stops when a slice starts red.
- **Experience First.** Product, UX and scope trade-offs are the product owner's, at Ready and on the wireframe, never the AI's.
- **Never Block on the Human.** People decide before the fact where the tiers file's decisions table lists a decision; elsewhere a stage states what it did and goes on (ADR 0026), which is aidlc's bounded form of it.
```

Two wording points. (a) "PRs" and "subagents" stay as pstack wrote them; `unslop` keeps quoted text as is. (b) The
`using-aidlc` bullet "**The map** is this skill, `using-aidlc`: the stages in order, the routes, and the practice for
each kind of work" (`skills/using-aidlc/SKILL.md:15`) gains ", and the principles index, whose leaves are the
`principle-*` skills, read by path". That keeps "aidlc has four kinds of skill." true: the leaves are the map's, not a
fifth kind a person starts. `scripts/test_parallel_lanes.py:1134` asserts that sentence, and `:1130` asserts the
README's "four kinds of skill (stage, practice, workflow and map)"; a fifth kind would change both assertions, which
needs the design change to say so.

---

## 6. Reading the index, the decision log, and the checks

### Where the index is read

pstack's shape: `PM:31-33` holds the index and says "Read the leaf skill in full for any principle you apply";
`PM:15` makes the reply "name each principle that shaped a decision ... Cite only principles whose leaf SKILL.md you
read this session"; `skills/figure-it-out/SKILL.md:13` opens its todo list with reading the index; and the delegate
wrapper `agents/poteto-agent.md:10` reads `poteto-mode` "in full, including its inline Principles index" and
"Navigate[s] to a leaf `principle-*` skill whenever you apply that principle". pstack's `worker.md` itself names no
principle. aidlc's equivalents are `story-run` (the runner), `lane-run`'s `worker.md` (worker plus wrapper) and
`aidlc-start` (the first stage).

| Entry point | Proposed text | Words | Limit |
|---|---|---|---|
| `skills/story-run/SKILL.md`, Inputs (after `:33`) | "- The principles index in `using-aidlc`, beside this skill's folder: read it at the start. Before you apply a principle, read its leaf, `../principle-<name>/SKILL.md`, in full, and name it in the decision log's why." | ~35 | **over**: 2,298 + 35 > 2,300. Raise RUN_LIMIT to 2,340 (`scripts/test_connect_flow.py:549`, with its comment, as each plan has). |
| `skills/lane-run/references/worker.md`, a bullet after `:9` | "- Before any work, read the principles index in `using-aidlc`, beside the `lane-run` folder. Read a principle's leaf in full before you apply it, and name each one that shaped a choice in your report." | ~35 | worker 291 < 300 fits; lane-run total 3,879 + 35 > 3,900: **raise** `scripts/test_parallel_pstack.py:216` to about 3,950. |
| `skills/lane-run/SKILL.md` | Nothing: step 5 (`:110-112`) runs `story-run` in full, which reads the index. | 0 | — |
| `skills/aidlc-start/SKILL.md:71`, step 6 | "6. **Route.** Load the `using-aidlc` skill for the routes and its principles index." | +4 | fits (39 left). |
| `skills/aidlc-build/SKILL.md` | Nothing needed when `story-run` runs it. Optional, for a build a person starts by name: at step 4 (`:43`), "a principle the playbook names is `../principle-<name>/SKILL.md` from this skill's folder". | ~14 | **over** (6 left): raise `scripts/test_references.py:295` or leave it to the index. |

The playbooks cite a principle by name only. The path rule lives once, in the index (a rule is written once, per
AGENTS.md). A stage started by name outside `story-run` reads the index only if it loads `using-aidlc`; today that is
`aidlc-start` (step 6) and `aidlc-plan` (step 7). That is the one gap; the optional build line closes it.

`parallel-lanes` needs nothing: its sub-agent lanes and reviewer briefs open with the `worker.md` line
(`skills/parallel-lanes/SKILL.md:147,152`). In a plain `story-run`, `aidlc-build` step 9 sends the reviewer agents no
`worker.md` line; the two agent citations in section 4 (`agents/reviewer-tests.md:25`, `agents/explorer.md:18`) name the
leaf, and the brief gives the path. That is enough, because reviewers judge and write no decision-log row.

### The decision log

The row is fixed by tests in three places: `scripts/test_route_and_log.py:23` (ROW, the template's last line, checked
at `:358`), `:370-385` (the row in `aidlc-build` step 7), and `:451` (the pull request description). Keep its five
fields. The principle goes inside `<why>`.

- `skills/aidlc-build/assets/progress-note.md:34-40`, in the paragraph above the row (no limit): "Name in `{{why}}`
  the principle that shaped the call, as `principle-<name>`, when one did, and only one whose leaf you read in this
  session; list each leaf read under Skills loaded." Example row:
  `- 3f2a1b9 · one table for the label rules · two call sites repeated the same branch (principle-model-the-domain) · src/labels.py:12 · owner the code owner`.
- `agents/reviewer-compliance.md:33-44` (no limit), after "a row missing one of them is a low finding": "A row that
  names a principle names one whose leaf the note's Skills loaded lists; a principle not read is a low finding. A row
  with no principle is not a finding. A principle never turns a stop into a row: a row that cites one for a file
  outside MAY CHANGE, a deleted test or a changed assertion is still the high finding above."
- `skills/aidlc-build/SKILL.md:46` step 7: leave it (6 words left). The template is where the row is written from.
  If the owner wants the sentence in the skill too: "In `<why>`, name the principle behind the call (`principle-<name>`)." (~10 words), with the limit raised.
- `skills/*/assets/tiers.md:44` (seven identical copies): no change; it says what the log is, not how a row reads.

"Each decision-log row naming the principle behind its choice" is kept as pstack words it, "each principle that
shaped a decision" (`PM:15`), not "every row names one". A name choice or a test's shape often has no principle, and
a forced citation is the "principle citation with no decision behind it" `docs/guide/08-principles.md:27` warns about.
If the owner wants every row to say something, `<why>` can end `(no principle)`; that adds noise without proof.

### Validator and tests

The leaves as pstack writes them fail today's validator in one place, and pass the rest:

- **"Use when".** Every leaf description starts "Apply when", "Apply to" or "Apply before/after"; none says "Use when".
  `scripts/validate.py:138-139` requires it. Keeping pstack's words needs an exemption by kind.
- **A new kind.** `metadata.kind: principle`, `metadata.invocation: manual`, and `disable-model-invocation: true`, as
  pstack sets it. In `scripts/validate.py`: `KIND_PRINCIPLE`, and for it: the folder starts `principle-`; the front
  matter has `disable-model-invocation: true`; the description starts "Apply" (in place of "Use when"); no
  `GATE_SECTIONS` heading; no "Load the `x` skill" phrase; and every folder named `principle-*` has the kind. The open
  format otherwise holds (`name` equals the folder; description at most 1,024 characters; the 21 pass both).
- **No gate line.** `GATE_LINE` ("You draft; you never approve.") is required only by `check_sections`, which an
  open-format kind skips. Do not add it to the leaves: it would change pstack's words, and the index (in
  `using-aidlc`, which ends with it, `:112`) carries it.
- **Never "Load the".** `scripts/test_loads.py:79` fails any loaded skill with `disable-model-invocation: true`, and
  `:72-73` would count a principle as a stage's practice. So no file may write "Load the `principle-x` skill"; cite with
  a bracket or "as `principle-x` says". The playbook test already forbids "Load the" in playbooks
  (`scripts/test_connect_flow.py:1038`).
- **Playbook sentences.** A citation sentence in a playbook must not contain "stop" or "stops"
  (`scripts/test_connect_flow.py:956,1040-1041`), or it must point to a Stop if listed in POINTERS.
- **Portability.** The leaves contain no `/aidlc:`, `$ARGUMENTS` or `${CLAUDE_...}` (`scripts/validate.py:49`) and no
  harness command, so `portability()` passes.
- **route_check.** It skips skills with `disable-model-invocation: true` (`scripts/route_check.py:48`), so the leaves
  add no collision.
- **A new test, `scripts/test_principles.py`.** Exactly the 21 leaf folders exist and the three left out do not; each
  leaf's description and heading match pstack's (copied once, as data in the test); the index lists the 21 under the
  five group headings in `PM`'s order, plus the three "Left out" lines; every `principle-<name>` named anywhere under
  `skills/` and `agents/` is a folder; no principle is cited more than three times outside `using-aidlc`; the
  `story-run` Inputs line, the `worker.md` line and `aidlc-start` step 6 name the index; each leaf with a conflict in
  section 4 ends with its "**In aidlc.**" line; the progress-note template and the compliance reviewer carry the
  decision-log sentences.
- **Elsewhere.** `skills/NOTICE:28-32` lists what aidlc adapted from pstack; add the 21 leaves and the index. An ADR
  (0031) records the decision, the three left out and why. `AGENTS.md` Standards (`:26-31`) and
  `docs/codebase-map.md:12,32-35` say where a principle leaf goes. `README.md:105-107`'s three-column table is
  asserted exactly (`scripts/test_parallel_lanes.py:1123-1124`): name the leaves in a line under it, not a fourth
  column. Raise the plugin's version (`.claude-plugin/plugin.json`).

---

## 7. Risks

**Description overlap, if a leaf could be model-invoked.** The leaves stay `disable-model-invocation: true`, so this
is a risk only if the flag is dropped, or on a host that ignores it (the Agent Skills format does not require the
field; aidlc already relies on it for eleven stages and three workflows). Measured with `scripts/route_check.py`'s
own TF-IDF, each leaf against aidlc's auto skills: the highest pairs are test-behavior and `writing-tests` 0.39,
test-behavior and `debugging-failures` 0.31, attack-the-premise and `writing-tests` 0.25, migrate-callers and
`migrating-safely` 0.22. All are under route_check's 0.75 collision line, but that check is lexical. By meaning the
real collisions are:

| Leaf (if auto) | Would compete with | Why it matters |
|---|---|---|
| `principle-build-the-lever` ("Apply to any non-trivial work") | every skill | It matches almost any request and would load on most turns. |
| `principle-fix-root-causes` ("Apply when debugging"), `principle-attack-the-premise` | `debugging-failures` | The practice owns the steps and the three-attempt limit. |
| `principle-test-behavior-not-implementation` | `writing-tests`, `reviewer-tests` | Its "Rewrite or delete the rest" would arrive without the practice's "never touch an existing assertion". |
| `principle-explain-the-number` | `tuning-performance` | Points to a skill aidlc lacks. |
| `principle-laziness-protocol`, `principle-subtract-before-you-add`, `principle-minimize-reader-load` | `simplifying-code`, `reviewing-code` | Three short rules would outrank the practice that holds the pin-first step. |
| `principle-boundary-discipline`, `principle-type-system-discipline`, `principle-make-operations-idempotent` | `designing-apis`, `securing-code` | Same subject, no aidlc bounds. |
| `principle-migrate-callers-then-delete-legacy-apis` | `migrating-safely` | The leaf's internal-only conditions are easy to miss. |
| `principle-separate-before-serializing-shared-state`, `principle-encode-lessons-in-structure`, `principle-redesign-from-first-principles` | `parallel-lanes`, `aidlc-feedback`, `aidlc-design` (all manual) | They would start outside the stage that bounds them. |

The flag also leaves 21 entries a person can type (`/aidlc:principle-...`). That is harmless and matches pstack
(`skills/poteto-help/SKILL.md:134`: "Typing `/principle-<name>` still loads one on demand").

**Contradictions with aidlc gates.** Nine leaves carry words that cross a gate when read alone: 3 (every reference;
redesign in a build), 4 (the next fix after two failures), 7 (the AI commits to a choice), 8 (first unit by hand; a
file in the diff), 12 (a stale leftover), 13 (delete and update tests), 15 (commit the trail only sometimes;
self-verification), 17 (a red commit first), 18 (rewrite or delete tests). The worst are 13 and 18: both tell the
reader to delete or rewrite tests, the one thing AGENTS.md's Boundaries forbid without a stop. Three layers keep the
gates: the index's header ("A principle explains a choice; it never permits one. Where a leaf's words differ from a
stage's gate, the gate holds"); each leaf's "**In aidlc.**" line; and the compliance reviewer's rule that a principle
never turns a stop into a row. The leaves are read only by path, from a stage or a playbook that holds the gate, so
the leaf never arrives alone.

**Principle theatre.** Asking each row to name a principle invites names with no decision behind them. pstack's own
eval playbook warns against grading by such self-report: "Don't ask the candidate to list which skills, principles, or
files they applied ... grade chain-following from code shape, not self-report" (`PB/eval.md:9`). The "only a leaf you
read" check, and "no principle" being no finding, keep the log honest. An eval case should grade the code's shape (a
table where branches were, a premise written before a third attempt), not the citation.

**Word limits.** `story-run` (2 left) and `lane-run` with `worker.md` (21 left) must have their limits raised for the
index reads; `aidlc-plan` (3 left) can take exactly the two one-word citations proposed; `aidlc-build` (6 left) takes
none unless its limit rises. Every other citation sits in a file with no limit.

**Short leaves.** Several leaves hold little beyond their description: `principle-exhaust-the-design-space` (one body
line), `principle-guard-the-context-window` (one bullet), `principle-laziness-protocol` (two bullets),
`principle-encode-lessons-in-structure` (starts with the judgement case). The earlier review checked these match
upstream. Read by path, the whole file, front matter included, is read, so the description carries the rule; a
reader who opens only the body gets less. The index lines, which repeat `PM`'s fuller wording, cover this.

**Dangling pointers.** Two leaves name pstack skills aidlc does not ship: `typescript-best-practices`
(`principle-type-system-discipline:15`) and `benchmark-checklist` (`principle-explain-the-number:14`, a relative link).
The validator checks only `assets/`, `references/` and `scripts/` paths. The new test should list every skill a leaf
names and require it to exist or to have an "In aidlc" redirect.

**The word "principle".** `skills/migrating-safely/SKILL.md` has a "## Core Principles" section, and other skills use
"principle" in prose. A reader may take those for the index's principles. Cite leaves only by their full
`principle-<name>`, never as "the principles".
