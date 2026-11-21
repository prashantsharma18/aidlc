# Slice 0: route G

Sent here from `aidlc-plan` after step 9, on slice 0 of route G; this skill's Gate, Stop if and Rules still apply.

Slice 0 (route G), the first slice of each new repository, on branch `feat/<KEY>-slice-0`:
1. RECIPE holds the SCAFFOLD commands of this repository's block in the approved `new-system.md`, marked `(scaffold)`.
   When SCAFFOLD is none, there is no RECIPE: the DO steps write the skeleton by hand, tests first. The bundle lists the
   approved DEPENDENCIES: the only dependencies the slice may add.
2. DO adds, tests first: a step that pins each direct dependency to the version DEPENDENCIES names (a package the
   generator added that DEPENDENCIES does not list is a stop for the design's approver, as this skill's Stop if says); one real test of behaviour; a
   health check that answers (an endpoint or a page); and the team's CI configuration (`.github/workflows/ci.yml` on GitHub,
   `.gitlab-ci.yml` on GitLab), which runs the COMMANDS, each check seen red once in a draft pull request.
3. MAY CHANGE covers the block's PATHS, the files the scaffold creates and the CI configuration. MUST NOT names
   `AGENTS.md`, `CODEOWNERS` and `.claude/**`. DONE WHEN: every command in
   `AGENTS.md` runs green locally, and CI runs them on the pull request.
4. The slice's stages mark the `slice 0` row in the index, not their own rows.
