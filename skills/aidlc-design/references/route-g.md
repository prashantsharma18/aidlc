# Route G: the new system

Sent here from `aidlc-design` step 1 of New system (route G); this skill's Gate, Stop if and Rules still apply.

1. Fill `assets/new-system.md` and write it to the story's folder as `new-system.md`: the stack and the architecture,
   with an ADR draft for each choice; every dependency named and pinned to a version, because approving this design is
   the approval to add them; the repository layout (one repository, or several, where the coordination plan holds one slice-0 part each; at a workspace root the coordination plan is written even for one repository); the contracts; a check for each non-functional requirement; the initial Quality bar targets,
   which the team sets; the commands for tests, lint, build and run; and the scaffold commands, at pinned versions,
   that slice 0 runs. Write one REPOSITORY block per repository: its stack, dependencies, paths, commands, scaffold and CI.
   Recommend one repository for code that ships together (ADR 0022); choose several only for a stated reason
   (different owners, release cycles or runtimes), recorded in an ADR draft.
