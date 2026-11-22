# Playbook: dependency bump

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `dependency-bump`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** One dependency moved to a new version, within the limits its class or its plan names, and nothing
else changed.

**Typical route.** S (a dependency-bump class in `AGENTS.md`), or F1.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `securing-code` when the bump answers a security advisory.

**Steps.**
1. Read the changelog or the release notes between the two versions, from the project's own source, and list each
   change that can reach this code: a removed or renamed API, a changed default, a new minimum runtime.
2. Change only the manifest and the lock file, with the package manager's own command, which writes the lock file.
3. Read the lock file's diff: every package it adds or moves. A package it adds is a new dependency, unless the class
   allows it, as `aidlc-build`'s Stop if says.
4. Run the full suite and the build, not only the tests near the change, and check each listed change of step 1.
5. A major version passes the class's limits, and a change the notes say needs code outside MAY CHANGE is a file
   outside it: both are a stop, as `aidlc-build`'s Stop if says, and the work takes its normal route.

**Its proof.** The manifest and lock-file diff (the evidence file's Dependency manifests section); the changelog read,
with each change that can reach this code and how it was checked; the full suite green.

**Hand back.** The versions before and after, the changes that can reach this code, and how each was checked.
