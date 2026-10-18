# Roles and ownership

Who decides, who owns which shared artefact, and who may approve.

## Owners of shared context and controls

| Artefact | Owner | Changes by |
|---|---|---|
| `AGENTS.md`, codebase map, folder rules, shared skills | Repository code owners | Reviewed PR |
| Harness: permissions, hooks, sandbox profile, check scripts | Harness code owner; platform team for the organisation layer | Reviewed PR, attack tests and evals |
| Eval set and baseline | Eval owner; baseline changes approved by a code owner, never the author | Reviewed PR |
| Acceptance criteria | Spec owner | Spec review loop (amendment with date, reason, decider) |
| Plans and briefs | Tech lead | Re-approval when scope, approach, risk or criteria change |
| Policies in `core/policy/` | The owner named in each policy's `meta` | Framework PR |

## The six judgement dimensions (people decide; automation informs)

Product intent · architecture fit · risk tolerance · security posture · test meaning · user impact.

## Approvals by tier

| Tier | Plan | Merge | Release |
|---|---|---|---|
| 1 | In the PR description | One code owner | Normal pipeline |
| 2 | Tech lead | Code owners of every affected area | Normal pipeline; flag where user-visible |
| 3 | Tech lead, approach approved before slicing | Plus a recorded specialist review | Named release approver; staged; rehearsed rollback |

The author never approves: not the engineer who directed the agent, not the identity that pushed
the branch, and never an AI reviewer.

Guide: 1.9, 11.6, 16.3.
