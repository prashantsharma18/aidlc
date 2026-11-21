# Choosing a tier

The eight stages always apply; the tier decides how much of each you do. The table is
[tiers-table.md](tiers-table.md); the skills carry the same table in their `assets/tiers.md`.

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

## Who decides at each tier

A person stops only where [the decisions table](tiers-table.md#decisions-by-tier) says so (ADR 0026). At Tier 1 that
is Ready and Merge, and Release only when users see the change. Tier 2 adds Design + plan, approved once in the pull request that merges them, and Release when
users see the change. Tier 3 adds the specialists, Release always, and the hands-on restatement per slice. Every other
stage states what it did and goes on; a person who disagrees says so.

Guide: 1.10.
