# Risk tiers

Rate each dial. The tier is the highest any dial reaches. When uncertain, go up a tier: unknown owners, unknown consumers or untested behaviour count as the next tier until someone resolves them. Scope alone never makes Tier 3; it raises coordination. A higher tier adds enforcement, checkpoints and approvers, never extra stages. A story that changes two or more repositories is at least Tier 2 (ADR 0021): its parts never merge on their own, and its release has a release approver. That approver decides only when users see the change.

| | Tier 1 · routine | Tier 2 · crosses a boundary or moderate risk | Tier 3 · high risk |
|---|---|---|---|
| Typical change | One repository, one owner, no contract change, familiar well-tested code | Crosses a contract or ownership boundary (public API, event, shared module, another team's code), moderate risk, or weak tests | Security, money, personal data, regulated behaviour, or legacy core code |
| Spec | A few lines on the work item: actor, observable behaviour, constraints, an example, a testable criterion | Written spec with non-goals; every edge-case concern decided; contract changes agreed with consumers; open questions owned | Specialist reviews the spec; every risk decision names its decider; data in the agent's context is classified |
| Design | Usually stops at step 1 with 'none needed', which the AI states in the plan; the code owner sees it at Merge | Every step, compactly | Specialist approval; threat model; NFRs tested before release |
| Plan | A brief for the fast path (`fix.md` for a defect, `brief.md` for a feature) or for a standard change (`standard.md`, route S); otherwise a short plan with one bundle per slice, which the AI states and the code owner reads at Merge | Written spec and plan; the tech lead approves design and plan in one pull request | Written plan with rollback; the approach is approved with the design, before slicing, in the same pull request as the plan |
| Verification | required CI checks | required CI checks, contract tests, integration environment | required CI checks, contract tests, integration environment, security or privacy tests, characterisation tests for legacy code |
| Approvals | Ready, then one code owner at Merge, who sees spec, plan and code together; no plan approval (except a plan with independent slices, ADR 0025) (the engineer confirms a fast-path or standard brief, with its tier) | Ready; design and plan, approved by the tech lead in one pull request; code owners of every affected area at Merge | Ready, with a specialist's spec review; design and plan, approved by the tech lead in one pull request, with the specialists; code owners of every affected area at Merge; recorded specialist review (security, privacy, architecture or release) |
| Agent autonomy (the bundle's MODE) | Any mode: hands-on, delegate with checkpoints, or delegate (a whole slice runs to DONE WHEN or the first STOP IF) | Hands-on, or delegate with checkpoints: a CHECKPOINT before each step that touches a contract or another owner's code | Hands-on only: judgement calls stay with a person; read-only first where code is poorly understood; no production access |
| Release | Normal pipeline; revert to roll back | Normal pipeline; flag where behaviour is user-visible | Staged release behind a feature flag; written stop criteria; rehearsed rollback; named release approver |
| Evidence pack items | none (notes in the PR) | 1, 2, 3, 4, 5 | 1, 2, 3, 4, 5, 6, 7, 8 |

## Decisions by tier

A person stops only where this section says so (ADR 0026). A stage that is not a decision for its tier still runs
and still writes its document. It states what it did, in the document and in the session, and goes on. A person who
disagrees says so, and the stage revises.

| Decision | Who | Tier 1 | Tier 2 | Tier 3 | Recorded |
|---|---|---|---|---|---|
| **Ready**: the work, its acceptance criteria, its tier and its route | product owner; the tier with whoever owns the risk (on F0, D1 and route S, the engineer who confirms the brief); the route is shown, and the tech lead owns it | yes | yes | yes, with a specialist's spec review | Tier 1: the decider's word in the session or their own tracker entry, checked (ADR 0023). Tier 2 and 3: the approval of the spec's pull request, which merges first (ADR 0020) |
| **Design + plan** | tech lead or architect | no | yes: one pull request approval that merges design and plan first | yes, with the specialists | the pull request approval |
| **Merge** | a code owner who did not write the change, after a non-author PASS, who reads the decision log with spec, plan and code | yes; the code owner sees spec, plan and code together | yes; every affected area | yes; the security specialist when the change touches secrets, permissions, tool calls, dependencies or prompts | the pull request |
| **Release** | release approver | only when users see the change | only when users see the change | always; a named approver and a rehearsed rollback | change management, cited in the readiness record |
| **Restatement** of a hands-on build | the engineer | no: stated | no: stated | yes, per slice | the progress note's `restatement confirmed by` line |

"When users see the change": a change behind a flag that is still off needs no release decision until the flag goes
on; turning a flag on is the release. The flag rule applies at Tier 1 and 2; at Tier 3 both the deploy and turning the
flag on are decided.

The route (ADR 0027): Ready shows it, and the tech lead owns it; the product owner sees it and does not decide it. A
technical person checks the ROUTE line's facts (the kind of work, the tier, the repositories the work changes, and
whether its criteria are written) at the first technical decision this table lists for the route: on F0, D1 and route
S, the engineer who confirms the brief, at Ready; on F1, D2 and C at Tier 1, the code owner, at Merge, where the pull
request description shows the ROUTE line (for a plan with independent slices, first the tech lead who approves it); at
Tier 2 and 3, the tech lead or architect, at Design + plan, in the same pull request; on route G, the tech lead or
architect who approves `new-system.md`. A route change after Ready that touches the tier, the scope, the criteria or
the controls is decided again, as `aidlc-start` says; a tier change, up or down, needs a new Ready; a lighter route is chosen only at the start; before Ready nothing is approved yet, so `aidlc-start` may still re-route to a lighter route.

The decision log (ADR 0027): the AI logs each judgement call it makes while building, one row each in the progress
note, and a row for each Deviation and Assumption; anything a skill says stops the work is a stop, never a row, and the pull request description groups the rows by owner. The code owner reads them at Merge, with spec, plan
and code. No row waits, and no one approves a row.

Where a pull request approval is the record, the AI writes the tracker entry from it, with how it was confirmed, and
asks before posting (ADR 0023). When the AI cannot read the review tool, the decider confirms in the session.

Kept at every tier, unchanged:
- A new dependency, a quality-bar exception, and an assertion change (the criterion's owner decides).
- The decisions a stage names inside its steps: a changed criterion and the parts it affects (route C), a contract
  change (its consumers), a wireframe for a new screen (the product owner), and an unproved criterion (whoever
  accepts it). At Tier 2 and 3, a contract change and a wireframe are approved in the pull request that merges the
  design and the plan.
- Checkpoints where the bundle's MODE puts them.
- The review of a recipe commit, except for a recipe class listed in `AGENTS.md`'s Standard changes on route S: the
  code owner reads its recipe check at Merge.
- The person pushes: the AI holds no push credential. The exception is ADR 0028: when the team's `AGENTS.md`
  says the AI may push its own feature branch, with a credential that cannot push the default branch, the AI
  pushes the story's own branches, only where a stage says to push and never to pause; never a force-push or a
  tag, and it never opens, closes, approves or merges a pull request.
- Every decision in operate, feedback and onboard, and every `parallel-lanes` person action.
- The AI never approves or merges (ADR 0023).
- A change of tier, up or down, is a Ready decision at every tier: the risk's owner decides it.
- A plan that marks its slices independent merges first at every tier (ADR 0025), so at Tier 1 too its tech lead
  approves it.
