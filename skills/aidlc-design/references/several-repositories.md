# Several repositories

Sent here from `aidlc-design` step 8, a story that spans several repositories; this skill's Gate, Stop if and Rules still apply.

1. For a story that spans several repositories, fill the coordination plan from `assets/coordination-plan.md`: one PARTS row per repository that changes (owner, change, flag, what it waits for, undo, status), the read-only repositories, the order (contract first, then the provider behind a flag that is off, then the consumers) and the rollback of each part. Write it to `stories/<KEY>/coordination-plan.md`.

For a story across several repositories, the home repository (the workspace root) holds the index, intent, spec, design note, ADR drafts, contract draft,
coordination plan, status, release records and incidents. Each part's repository holds its plan, bundles, criteria
copy, progress notes, evidence, pull request description, review record, its own ADRs and its code; the provider
holds the published contract.
