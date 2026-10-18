# Choosing a tier

The eight stages always apply; the tier decides how much of each you do. The policy is
`core/policy/tiers.yaml`; the table generated from it is [tiers-table.md](tiers-table.md).

## How to rate a change

1. Rate each dial: **risk** (the cost of being wrong), **complexity** (how well the code is
   understood and pinned by tests), **scope** (how many repositories and owners).
2. The tier is the highest any dial reaches. The dials are independent: a one-line change to an
   authorisation rule is tiny in scope and Tier 3 on risk.
3. When uncertain, go up a tier. Unknown owners, unknown consumers or untested behaviour count
   as the next tier until someone resolves them.
4. Scope alone never makes Tier 3; breadth raises coordination (cross-repository procedure), not risk.

## Examples

| Change | Dials | Tier |
|---|---|---|
| Fix a typo in an email subject | all low | 1 |
| Add an optional field to an API another team consumes | scope medium | 2 |
| Limit password-reset requests | risk high (security) | 3 |

A higher tier means more enforcement, checkpoints and approvers, never more stages.

Guide: 1.10.
