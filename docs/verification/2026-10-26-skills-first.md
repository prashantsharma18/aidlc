# Skills-first aidlc, end to end (Plan 7)

Run 2026-10-25 to 2026-10-26 on the demo workspace `~/work/shipment-tracking`. Claude Code headless sessions,
`--plugin-dir` pointing at this checkout (the repository root is the plugin), `--permission-mode acceptEdits`,
model Sonnet. No Python harness: the gates were the skills' text, the starter settings and the people.

## The work item

[SHIP-2](https://prashantsharma18.atlassian.net/browse/SHIP-2), filed as a Bug: the tracking page shows nothing about
delivery when the carrier's estimate is unusable. Expected: "No delivery estimate yet".

## What ran, where, and what it produced

| Step | Ran in | Output, kept at | Decision |
|---|---|---|---|
| `aidlc-start SHIP-2` | workspace root | Read the bug; explorers in both repositories (only customer-portal changes); found that SHIP-2 reverses SHIP-1's approved "no usable estimate, page unchanged"; asked five questions. `stories/SHIP-2/README.md` (the pointer) | Product owner: a change request superseding SHIP-1 AC9/AC10 for non-delivered shipments; flag order accepted; every status but delivered; same place as the window line |
| `aidlc-specify SHIP-2` | customer-portal | `plans/SHIP-2/spec.md`: AC1–AC9, E1–E16, a supersession table | Spec v1 approved; SHIP-1's spec got an amendment note |
| `aidlc-plan SHIP-2` | customer-portal | `plan.md`, `bundle-core.md`, `bundle-edges.md`. Found that no existing SHIP-1 assertion has to change | Plan approved |
| `aidlc-build SHIP-2 core` | customer-portal | 18 new tests red for the expected reason, then the one-file change; 111 tests green; the agent committed each step | - |
| `aidlc-build SHIP-2 edges` | customer-portal | Pin tests; six break-and-restore mutations each turned the right tests red; 125 tests green | - |
| `aidlc-verify SHIP-2` | customer-portal | `evidence.md` (local only: no CI), `pr-description.md`; flagged two out-of-scope settings commits | The person moved them to `main` |
| `aidlc-review SHIP-2` | customer-portal | Three reviewer agents; no production defect, no security finding; 11 findings with dispositions; `review-record.md` | Code owner: fix F1, F3; accept F2, F10; fix F9 by hand; dismiss the rest |
| `aidlc-build` fix round | customer-portal | Flag-off tests wait for the config to be applied, proved by forcing the flag on (3 red, then restored) | Review approved; branch ready for a pull request |

Final state: `feat/SHIP-2-portal`, 11 commits; lint, typecheck and 125 tests pass; no existing test changed.

## Findings and fixes (all fixed in the framework during the run)

| ID | Finding | Fix |
|---|---|---|
| P7-F1 | The starter settings did not allow the tracker's read tools, so a headless session could not read the work item | Starter templates name the tracker; the quickstart says to allow its read tools and deny transitions |
| P7-F2 | At the workspace root, `aidlc-start` routed to one repository but could not write the index there | At a root, the index always goes to `stories/<KEY>/README.md` |
| P7-F3 | It then put the one-repository story's documents at the root | For one repository, the root index is only a pointer; every stage runs in the repository |
| P7-F4 | Story-level skills treated "a `stories/<KEY>/` folder exists" as "several repositories" | They follow the route written in the story's index |
| P7-F5 | A repository session could not read the workspace's `stories/` | Repository starter settings: `additionalDirectories: ["../stories"]` |
| P7-F6 | A skill could not read its own templates (the plugin lives outside the project) | Starter settings allow `Read(~/.claude/plugins/**)` |

The harness-era finding F13 (agents could not write `.git`) is gone: the build agent committed its own steps.

## Copilot, Codex, Cursor

- `customer-portal/.github/skills/` (21 skills) and `.github/agents/*.agent.md` (7 agents, without Claude's `tools:` line)
  are committed on `main` and the story branch. **To check in VS Code:** open `~/work/shipment-tracking/customer-portal`,
  switch Copilot Chat to agent mode, and ask "which skills do you have?" and "use the aidlc-start skill for SHIP-3". Not yet
  checked by the user.
- Codex and Cursor are not installed; the copied skills pass `scripts/validate.py`'s open-format checks (folder name
  equals `name`, a description with "Use when"), which is what both tools require.

## What the harness used to do, and what did it here

| Before | In this run |
|---|---|
| The guard refused edits outside the bundle | The build agent listed its diff against MAY CHANGE; verify and the compliance reviewer flagged the two out-of-scope commits |
| A check refused weakened tests | The planner proved no SHIP-1 assertion had to change; the spec named the one exception the owner allowed |
| The retry limit | Not reached; the skills' three-attempt rule stands |
| Approval lines in a file | Approvals recorded in the spec, plan and review record, and in the people's decisions in this page |
