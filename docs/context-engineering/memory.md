# Memory

Memory is what an agent or person keeps between sessions outside reviewed files. It is an inbox,
never the library. Policy: framework `core/policy/memory-policy.yaml`.

For a developer:
- Use it for non-sensitive preferences and working notes only; never secrets, customer data,
  production identifiers or unfixed vulnerabilities.
- It never wins a conflict. If it disagrees with code, rules or the spec, it is wrong.
- A lesson worth keeping becomes a PR to its proper home (rules, map, decision record, eval case)
  with evidence, an owner, a scope and a rollback path; then delete the note.
- Demo, eval and CI sessions run with auto memory disabled so results are reproducible.
- Session state (one task's progress) lives in the progress note on the branch, not in memory.

Guide: 2.10.
