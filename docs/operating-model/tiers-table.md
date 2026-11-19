<!-- The same table as skills/aidlc-plan/assets/tiers.md (copied into aidlc-start and aidlc-discover): change all four together. -->
# Risk tiers

Rate each dial. The tier is the highest any dial reaches. When uncertain, go up a tier: unknown owners, unknown consumers or untested behaviour count as the next tier until someone resolves them. Scope alone never makes Tier 3; it raises coordination. A higher tier adds enforcement, checkpoints and approvers, never extra stages. A story that changes two or more repositories is at least Tier 2 (ADR 0021): its parts never merge on their own, and its release has a release approver.

| | Tier 1 · routine | Tier 2 · crosses a boundary or moderate risk | Tier 3 · high risk |
|---|---|---|---|
| Typical change | One repository, one owner, no contract change, familiar well-tested code | Crosses a contract or ownership boundary (public API, event, shared module, another team's code), moderate risk, or weak tests | Security, money, personal data, regulated behaviour, or legacy core code |
| Spec | A few lines on the work item: actor, observable behaviour, constraints, an example, a testable criterion | Written spec with non-goals; every edge-case concern decided; contract changes agreed with consumers; open questions owned | Specialist reviews the spec; every risk decision names its decider; data in the agent's context is classified |
| Design | Usually stops at step 1 with a recorded 'none needed' | Every step, compactly | Specialist approval; threat model; NFRs tested before release |
| Plan | A brief for the fast path (`fix.md` for a defect, `brief.md` for a feature); otherwise a short plan with one bundle per slice | Written spec and plan; tech lead approves the plan | Written plan with rollback; approach approved before slicing |
| Verification | required CI checks | required CI checks, contract tests, integration environment | required CI checks, contract tests, integration environment, security or privacy tests, characterisation tests for legacy code |
| Approvals | one code owner; tech lead approves the plan (the engineer confirms a fast-path brief) | code owners of every affected area, tech lead approves the plan | code owners of every affected area, tech lead approves the plan, recorded specialist review (security, privacy, architecture or release) |
| Agent autonomy (the bundle's MODE) | Any mode: hands-on, delegate with checkpoints, or delegate (a whole slice runs to DONE WHEN or the first STOP IF) | Hands-on, or delegate with checkpoints: a CHECKPOINT before each step that touches a contract or another owner's code | Hands-on only: judgement calls stay with a person; read-only first where code is poorly understood; no production access |
| Release | Normal pipeline; revert to roll back | Normal pipeline; flag where behaviour is user-visible | Staged release behind a feature flag; written stop criteria; rehearsed rollback; named release approver |
| Evidence pack items | none (notes in the PR) | 1, 2, 3, 4, 5 | 1, 2, 3, 4, 5, 6, 7, 8 |
