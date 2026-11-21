# Roles and ownership

Who decides, who owns which shared artefact, and who may approve.

## Owners of shared context and controls

| Artefact | Owner | Changes by |
|---|---|---|
| `AGENTS.md`, codebase map, folder rules, shared skills | Repository code owners | Reviewed PR |
| Skills, agents and starter settings | Framework owners; platform team for the organisation layer (managed settings) | Reviewed PR; `scripts/validate.py` green |
| Eval set and baseline | Eval owner; baseline changes approved by a code owner, never the author | Reviewed PR |
| Acceptance criteria | Spec owner | Spec review loop (amendment with date, reason, decider) |
| Plans and briefs | Tech lead (a brief: the engineer who confirms it) | Re-approval when scope, approach, risk or criteria change (at Tier 1, the plan is stated again, except a plan with independent slices, which the tech lead re-approves) |

## The six judgement dimensions (people decide; automation informs)

Product intent · architecture fit · risk tolerance · security posture · test meaning · user impact.

## Approvals by tier

| Tier | Ready | Design + plan | Merge | Release |
|---|---|---|---|---|
| 1 | Product owner (on F0, D1 and S, the engineer confirms the brief and its tier) | None: the AI states them, except a plan with independent slices, which the tech lead approves; the code owner reads them at Merge | One code owner, who sees spec, plan and code together | Only when users see the change; normal pipeline |
| 2 | Product owner, in the spec's pull request | Tech lead or architect, in one pull request | Code owners of every affected area | Only when users see the change; flag where user-visible |
| 3 | Plus a specialist's spec review | Tech lead or architect with the specialists; the approach is approved with the design | Plus a recorded specialist review | Always: named release approver; staged; rehearsed rollback |

At Tier 3 the hands-on build also waits for the person to confirm its restatement, once per slice. Every tier keeps
the decisions the tiers file lists under "Kept at every tier" ([tiers-table.md](tiers-table.md), ADR 0026).

The author never approves: not the engineer who directed the agent, not the identity that pushed
the branch, and never an AI reviewer.

Guide: 1.9, 11.6, 16.3.
