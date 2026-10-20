# Trusted CI: `aidlc ci`

`aidlc ci` runs the mandatory gates against a task branch, with everything that judges the change
taken from the base branch. It is the check that counts toward a merge. Every result is labelled
`simulated-ci`, because no Git host enforces it yet (design §8, §13).

The code is `cli/aidlc/ci.py` and `cli/aidlc/sandbox.py`. The steps are those of the
[one-command check](README.md), plus two that only CI runs: `config-policy`
([policy as code](policy-as-code.md)) and `protected-rerun`. The change's own code runs in a
sandbox.

## The trust order

The change's install script and tests were written by an agent. If they ran first, they could
rewrite the judges. So the order is the security property:

1. **Prepare.** Get checkouts of the base and the head. Read every piece of
   evidence: configuration, approvals, merge approvals, the skip allow-list. Load every judge.
   Build the protected re-run's checkout.
2. **Judge.** Run `scope`, `protected-tests`, `secrets`, `context-drift` and `config-policy` from
   git objects and the untouched checkout.
3. **Run the change's code, sandboxed.** The repository's command steps run in bubblewrap. Then
   the steps that read their output: `skips` and `protected-rerun`.
4. **Verdict.** Decide merge readiness from the evidence read in step 1, and write the record.

No git command reads or runs in the change's working tree after step 3 starts. The change's code
could have planted git configuration or attributes there. Clean-up of the worktrees runs git from
the main repository or the common git directory, never from the change's worktree, and with hooks
disabled. The sandbox bound the common git directory read-only, so the change could not alter it.

## What comes from the base branch

| Evidence | Source |
|---|---|
| `commands`, `check_steps`, `test_reports`, the profile and the base branch name | `.aidlc/config.yaml` in the base checkout |
| The task scope | The bundle approved in `plans/approved-bundles.txt`, pinned by a full commit SHA that must resolve to itself; a short SHA fails `scope` |
| Merge approvals | `plans/approved-merges.txt` |
| Declared skips | `test/allowed-skips.txt` |
| Policy data for `config-policy` | The base checkout's effective permissions |
| The judges, the Rego pack and the renderer | The framework checkout, never the repository |

In local mode even the base branch's name is trusted data. `aidlc render` records it outside the
repository when you render on the base branch and no record exists yet. To change it, check out
the new base and run `aidlc render --tool claude-code --trusted-base NAME`. If the record is
missing, or the base's configuration names another branch, `aidlc ci` stops and says so.

The base commit is trusted data too. An agent shell can move `refs/heads/<base>` with a plain
redirect into `.git/refs/heads/`, and no git command is involved for the guard to deny. So local
mode never trusts the live ref on its own. It reads the commit that `aidlc scope` pinned in the
branch's scope file, the `base:` line. That file lives under `~/.aidlc` (`AIDLC_HOME_DIR`), where
agents cannot write. The base checkout is that pinned commit. If the scope is missing or
unreadable, or the live ref no longer equals the pinned commit, `aidlc ci` exits 2:

```text
the base branch moved since the scope was generated (scope base <sha>, main now <sha>); a person must re-run aidlc scope --branch <task branch> --accept-base <live sha> after reviewing these commits (! = touches approvals, skips, exceptions or configuration):
  ! <sha> <author> <<email>> <subject>  (touches plans/approved-merges.txt)
    <sha> <author> <<email>> <subject>
```

A refusal is not the end of a forgery. The forged commit is now the base, so a plain re-scope
would read approvals from it and pin it. That is why re-scoping after the base moved is a
confirmation step, not a formality:

1. `aidlc scope --branch <task branch>` sees that the scope already pins another base. It lists
   every commit from the pinned base to the live one, and marks with `!` each commit that touches
   `plans/approved-bundles.txt`, `plans/approved-merges.txt`, `test/allowed-skips.txt`,
   `test/protected-exceptions.txt`, `.aidlc/config.yaml` or `.aidlc/permissions.yaml`. It warns
   when the pinned base is not an ancestor of the live one (rewritten history). Then it exits 2.
2. You read the list. A commit you do not recognise, above all one marked `!`, is the forgery:
   reset the base branch to the commit it should be, and do not accept it.
3. When every commit is one you expect, such as another merge, you run
   `aidlc scope --branch <task branch> --accept-base <live sha>`. The value must be the full live
   commit, exactly; an abbreviation or any other commit is refused. Then you run `aidlc ci`.

A first scope, with no scope file yet, needs no flag. Agents cannot accept a base, because the
scope lives under `~/.aidlc` and the sandbox denies them writes there. The shell deny rule
`aidlc scope*--accept-base*` is defence in depth only: wrappers such as `python3 -m aidlc` get
past a pattern. The `!` marker does not cover test files, so review every listed commit, not only
the marked ones.

## Local mode and GitHub mode

**Local mode** is `aidlc ci [--repo PATH] [--branch NAME] [--group NAME]`. It checks out the base
(the commit pinned in the scope file) and the head as detached worktrees in a private temporary
directory, and always removes them:
Python deletes the folders, then git drops its record of each. It requires the sandbox. It
refuses to check the base branch itself, and needs `--branch` on a detached HEAD.

**GitHub mode** is what the workflow runs. It needs `--trusted`, `--head`, `--branch`,
`--head-sha` and `--records` together. It runs only inside GitHub Actions. `--head-sha` must be
the full commit checked out in `--head`, so the pull request head, never the merge ref. The
records directory must not exist yet and must lie outside the pull request checkout.

Either mode refuses a change that tracks files under `.check/` or `.aidlc/ci-records/`. A
malformed `check_steps`, `profile` or `ci` value exits 2.

## The sandbox

The change's commands run in bubblewrap. The root is an allow-list, not a read-only copy of `/`:
a read-only bind does not stop `connect()` on a Unix socket. On a WSL host, `/mnt` alone held 33
reachable sockets, including Docker Desktop, an HTTP proxy, an ssh agent and the real home.

| Inside the sandbox | Policy |
|---|---|
| `/usr`, `/etc`, `/opt` | Bound read-only |
| `/bin`, `/sbin`, `/lib*` | Recreated as the host's symlinks, or bound read-only where they are folders |
| `/dev`, `/proc` | Mounted fresh |
| `/tmp`, `/run` | Empty tmpfs, so no host sockets |
| `/home`, `/root`, `/mnt`, `/var`, `/srv`, `/media`, `/snap` | Absent |
| `$HOME` | A private per-run directory, discarded afterwards |
| Toolchains under home | The profile's `ci_sandbox_read` paths, read-only |
| The checkout | The only writable tree. Its `.git` and the common git directory are bound read-only on top |
| Environment | Cleared, then `PATH`, `LANG`, `LC_ALL`, `TERM`, the profile's `ci_sandbox_env`, `HOME`, `TMPDIR` and `CI` |
| Network | None, except the install step (`install` or `restore`). It gets the resolver file alone, never its folder |
| Processes | Own PID, IPC and UTS namespaces; the tree dies with its parent |

Local mode never runs the change's code unsandboxed, and refuses `--sandbox auto`. In GitHub
mode, `compile` and `check` use `--sandbox require`, and `scans` uses `--sandbox auto`, because it
runs none of the change's code. The exact rule: `auto` falls back to no sandbox only for `scans`.
Any other group fails if bubblewrap cannot start, whatever the mode. The record's `sandbox` field
says `bwrap` or `none`.

Profiles come from the framework's `core/context/profiles.yaml`. An unknown profile, a malformed
`ci_sandbox_read` or `ci_sandbox_env`, or a read path that is not strictly under home is an error.

### Known limits

- **The install step shares the host network.** Package registries need it. It can reach
  localhost services and abstract Unix sockets in the host network namespace; on a Linux desktop
  that includes X11.
- **Proxies reach the install step only.** It receives `HTTPS_PROXY`, `NO_PROXY` and the CA
  variables. No other step does.
- **Toolchains must live in `/usr`, `/opt` or home.** A toolchain under home is added through
  the profile's `ci_sandbox_read`, which accepts only paths strictly under home. One installed
  anywhere else, such as `/srv` or `/var`, cannot be made visible at all; install it in one of
  those places instead.
- **Self-hosted runners.** The workflow's `sysctl` step relaxes
  `kernel.apparmor_restrict_unprivileged_userns` for the whole host, and the change persists.
  Platform owners decide whether to allow that, or configure the runner so bubblewrap works
  without it.

## The protected re-run

The change's tests may only gain lines. But an added line, or an added test file, can still hide
a regression. So CI re-runs the base test suite on the new code (guide 9.5).

The re-run happens only when the change modifies, retypes, deletes or adds a test-pattern file,
and only in a full run or `--group check`. Otherwise the step reports `ok` with "no existing test
file changed".

When it runs, it has its own third worktree, built in step 1, before any of the change's code runs:

- every test file the change modified, retyped or deleted gets its base bytes and mode back,
  unless an approved exception covers it;
- every test file the change added is removed;
- the first run's sandbox never sees this worktree;
- its `.check/` is prepared there too, so the re-run's logs never go to the first run's
  `.check/`, which the change's code controlled. The record names them `rerun/.check/<step>.log`.

It then runs in its own sandbox with a fresh private home: the install step again, the
compile-type steps, then `test`. On .NET, the rebuild means the base tests really run, not the
change's already-built binaries.

> ⚠️ **Watch out:** Files outside the test patterns can still steer the re-run: `conftest.py`,
> runner settings in `package.json`, build files. The scope check and AI review (Plan 4) cover
> those.

## Groups and merge readiness

| Group | Branch-protection job | Steps |
|---|---|---|
| `compile` | `compile` | The install step and the compile-type steps |
| `check` | `check` | `scope`, `protected-tests`, `context-drift`, every command step, `skips`, `protected-rerun` |
| `scans` | `scans` | `secrets`, `config-policy`; no change code |

The required job names are in `core/policy/branch-protection.yaml`. A run is merge-ready only
when it is a full run (no `--group`), every gate passes, and the base's `plans/approved-merges.txt`
holds a line `<branch> <full head sha> <approver> <date>`. A new commit needs a new approval line.

## The record

Each run writes one JSON record. Locally it goes to `.aidlc/ci-records/`, which ignores itself.
On GitHub it is the job's artifact. The fields are `label`, `framework`, `branch`, `head`,
`base_branch`, `base`, `group`, `sandbox`, `result`, `failures`, `steps`, `merge_ready`,
`merge_ready_reason`, `time` and `record_sha256`.

The GitHub jobs always pass `--group`, so their records are never `merge_ready` (the reason says
"partial run"). There, branch protection's required jobs decide. Locally, merge readiness needs a
full `aidlc ci` run.

`record_sha256` is the SHA-256 of the record without that field. Check it, and check that `head`
is the branch tip, before you rely on a record:

```bash
PYTHONPATH=<framework>/cli python3 -c '
import json, sys
from aidlc.ci import verify_record
record = json.load(open(sys.argv[1]))
print("intact" if verify_record(record) else "EDITED", record["head"])' .aidlc/ci-records/<record>.json
git rev-parse <branch>
```

The hash is unkeyed. It detects an edit after writing; it does not prove who wrote the record.
Trust comes from where the record was written. Agents cannot write there: the session sandbox
denies writes to `.aidlc/`, and the `Edit` rules deny it too. A record committed on a branch can
still appear in `.aidlc/ci-records/` while that branch is checked out, which is why the head check
matters.

## The GitHub workflow

Add `ci: [github]` to `.aidlc/config.yaml` and render. The workflow appears at
`.github/workflows/aidlc-verify.yml`, from `core/ci/github/aidlc-verify.yml`. It stays inactive
until the repository has a remote. Set two repository variables:

- `AIDLC_FRAMEWORK_REPO`, the framework repository;
- `AIDLC_FRAMEWORK_REF`, a full commit SHA. The job fails if it is anything else.

Each job checks out the pull request head (`pr/`), the base commit (`trusted/`) and the framework,
all without persisted credentials, and with a read-only token.

**Branch names.** Approvals are keyed on the branch name. The workflow passes the pull request's
branch name only when its head is in this repository. A pull request from a fork runs as
`fork-pr-<number>`, so a fork that names its branch after an approved one gets no approval. The
name is computed in `env:` and used as `"$BRANCH"`, never written into `run:`.

**Toolchain files.** The node profile needs `.nvmrc` at the repository root, and dotnet needs
`global.json`. Doctor D14 fails without them. The toolchain version comes from the change by
design, so review it like code.

**The trust boundary.** On `pull_request`, GitHub runs the pull request's own copy of the
workflow, so a change can edit it. Its integrity rests on review: CODEOWNERS must cover
`/.github/` and `/.aidlc/` with required code-owner review (`code_owned_paths` in the
branch-protection policy), or an organisation required-workflow ruleset must pin it by SHA. The
same list names the evidence CI reads from the base: `/plans/approved-bundles.txt`,
`/plans/approved-merges.txt`, `/test/allowed-skips.txt` and `/test/protected-exceptions.txt`. A
change to any of them reaches the base only with a code owner's approval.

**Governance.** Once the base branch lists `ci: [github]`, a change that drops it fails
`config-policy`. Turning CI off takes a reviewed change to the base, made by a person.

## Testing it

`make test` skips the tests that need bubblewrap when it cannot start a sandbox. `make
sandbox-test` runs `tests/unit/test_sandbox.py` and `tests/unit/test_ci.py` and fails if any test
is skipped, as `make policy-test` does for conftest.

## Limits

- No Git host exists, so branch protection is simulated. Merge readiness is a record, not a
  blocked button.
- Plan 4 adds the remaining required jobs: `agent-config-evals` and `ai-review-dispositioned`.
- Every sandboxed step, the networked install step included, can read the common git directory.
  The sandbox binds it read-only, because git needs it, but it is not filtered. In local mode
  that is your whole `.git`: every branch and its history, and `.git/config` with any
  credentials written into a remote URL. The install step can also send what it reads over the
  network. Keep credentials out of remote URLs (use a credential helper), and treat a branch
  that is not ready to share as visible to the change under test.

Guide: 3 step 6, 9.5, 9.7, 11.8.
