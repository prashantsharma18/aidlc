# Hooks

Hooks are scripts the tool runs before and after each tool call. The pre-tool guard can stop a
call. The post-tool check cannot undo one, so it flags. Both live in `core/hooks/`, use only the
standard library and make no network calls.

Rendered copies appear in a repository's `.aidlc/hooks/`. Never edit them. Edit the sources in
`core/hooks/` and render again.

## The contract

The Claude shim (`core/hooks/claude_shim.py`) turns the tool's payload into a generic request
and back. The full contract is in [the adapter interface](../adapters/interface.md).

- The guard returns `allow`, `ask` or `deny`. `allow` means "no objection". Permissions and the
  sandbox still apply.
- The shim prints nothing for "no objection". It never prints an `allow` decision.
- Anything unexpected is a `deny` (pre) or a `flag` (post). The shim exits 2 on any internal
  error, which the tool treats as a block, and writes a `fail-safe` record to the decision log.
  The settings also set `onFailure: block`, so a crash or a timeout blocks too.

## Which tools reach the hooks

Every tool call reaches the pre-tool guard: the rendered `PreToolUse` matcher is `.*`. The shim
sorts each tool into a class (`CLASSES` in `core/hooks/claude_shim.py`):

- Read and control tools (`Read`, `Glob`, `Grep`, `LS`, `NotebookRead`, `TodoWrite`, `Task`,
  `Agent`, `ToolSearch`, `BashOutput`, `KillShell`, `KillBash`, `ExitPlanMode`, `EnterPlanMode`,
  `Skill`, `SlashCommand`, `AskUserQuestion`, `ListMcpResourcesTool`, `ReadMcpResourceTool`)
  are class `read`. The guard allows them.
- `Edit`, `Write`, `MultiEdit` and `NotebookEdit` are `edit`. `Bash` and `Monitor` are `shell`.
  `WebFetch` and `WebSearch` are `external`. Every `mcp__*` tool is `mcp`.
- Any other tool is `unknown`. The guard asks a person (rule `unknown-tool`), which is a deny in
  unattended runs. A new tool therefore never runs silently, and never hard-breaks an
  interactive session either.

The `PostToolUse` matcher is `^(Edit|Write|MultiEdit|NotebookEdit|Bash|Monitor|BashOutput)$`.
`BashOutput` returns a background command's output, so the post-check scans it for
credentials only.

Claude Code does not fire `PostToolUse` for a Bash call that exits non-zero. It fires
`PostToolUseFailure` instead, so the settings register that event too, with the same matcher.
The shim runs it as phase `post-failure`: the same post-check, on the error text, with the exit
code parsed from it. A failing `echo x > api/x.yaml; exit 1` is still flagged.

> 💡 **Tip:** When a tool you use every day keeps asking with `unknown-tool`, add it to
> `CLASSES` in the source, render, and add a test. Do not widen anything else.

## The rules and their reasons

`core/hooks/README.md` lists every check. In short:

| Rule | Reason |
|---|---|
| Edits must stay inside the repository and inside the task scope | The task bundle approved on the base branch defines what may change |
| Protected paths are always denied | The agent must not weaken the controls that judge it |
| Shell commands are matched against `shell_deny` after normalisation | Wrappers, substitutions and absolute paths must not hide `git push` |
| Git commands that move the base branch are denied (`base-ref`) | The base branch is the trust root for approvals and the post-check |
| Piping into a shell is denied; a nested shell asks | The inner command cannot be judged |
| MCP tools are matched against `tool_deny` and `tool_ask` | Tracker writes need a person |
| External reach always asks | Retrieved text may be hostile |
| Post-check: a high-confidence credential in output, a new or changed protected path, writes outside scope, a changed or removed assertion, a disabled test or narrowed suite (`skipped-test`: `.skip`, `.only`, `[Fact(Skip=...)]`, `@Disabled` and similar) | The fast first line before trusted CI |

## Rule ids

Every decision carries a `rule`. It appears in the decision log and in the reason the agent
sees, as `[aidlc <rule>]`. The ids below are the ones the code emits.

| Rule | Hook | Decision | Meaning |
|---|---|---|---|
| `protected-path` | guard, post-check | deny, flag | The guard: an edit targets a protected path or `.git`. The post-check: a protected path is new or changed since the base, usually a shell write the `Edit` rules cannot see |
| `outside-scope` | guard, post-check | deny, flag | The path is not in the task's MAY CHANGE list |
| `outside-repo` | guard | deny | The edit resolves outside the repository, or the session is not in a git repository |
| `shell-deny` | guard | deny | A command matches a `shell_deny` pattern |
| `base-ref` | guard | deny | A git command would move, delete, rename or recreate the base branch |
| `recursive-delete` | guard | deny | `rm` with a recursive flag in any spelling |
| `nested-shell` | guard | ask | `bash -c`, `eval`, `source` or `env -S` hide the command that runs |
| `pipe-to-shell` | guard | deny | Output piped into a shell |
| `unparseable` | guard | ask | A part of the command could not be parsed |
| `tool-deny` | guard | deny | An MCP tool matches `tool_deny` |
| `tool-ask` | guard | ask | An MCP tool matches `tool_ask` |
| `external` | guard | ask | `WebFetch` or `WebSearch` |
| `unknown-tool` | guard | ask | The shim could not classify the tool |
| `no-scope` | guard, post-check | deny, flag | No readable scope file for the branch, or `AIDLC_SCOPE=off` when unattended |
| `hard-link` | guard | deny | The target file has more than one hard link |
| `fail-safe` | guard, post-check, shim | deny, flag | Unreadable input or harness data, an internal error, a command too large or complex, or output too large to scan |
| `changed-assertion` | post-check | flag | An existing assertion in a test file was changed or removed |
| `skipped-test` | post-check | flag | A test was disabled or the suite narrowed |
| `secret-in-output` | post-check | flag | Tool output contains a high-confidence credential shape |
| `check-recorded` | post-check | pass | A run of `aidlc check` was counted; the reason gives the failures in a row and the limit |
| `retry-limit` | post-check, guard | flag, deny | The failing runs in a row reached the limit, or the attempts record is unreadable. The guard then denies every edit and shell call until a person resets it |

No-objection ids, for reading the log: `read`, `in-scope`, `scope-off`, `integration` and
`no-guarded-command` (guard, allow), and `not-modifying` and `no-rule-broken` (post-check, pass).
In an `ask` or `deny` the reason ends with "(unattended run: ask means deny)" when the run is
unattended.

## The base branch and the post-check

The post-check diffs the branch against a base commit. The base comes from, in order:

1. `AIDLC_BASE_REF`, when set.
2. The `base:` line in the scope file. `aidlc scope` records the base branch's commit there when
   it generates the scope, outside the repository.
3. `harness.base_branch` (default `main`), only for scope files written before the base was
   recorded.

Moving the local base branch therefore hides nothing from the post-check. The guard denies the
usual ways to move it anyway: `git branch -f|-d|-D|-m|-M|-c|-C <base>`, `git update-ref
[-d] refs/heads/<base>` (and `update-ref --stdin`), `git checkout -b|-B <base>`, `git switch
-c|-C <base>`, and `git fetch|push <remote> <x>:<base>`. `git symbolic-ref HEAD
refs/heads/<base>` is allowed.

> ⚠️ **Watch out:** A local base branch is a simulated trust root. The guard cannot see a raw
> write such as `echo <sha> > .git/refs/heads/main`. Before the scope is generated, such a write
> can forge the approval that `aidlc scope` reads, so look at the base branch before you scope.
> After that, local `aidlc ci` refuses to run while the live ref differs from the commit pinned
> in the scope file. Once a remote exists, the GitHub workflow reads approvals from the pull
> request's base commit, behind branch protection ([trusted CI](../checks/ci.md)).

## Protected files that a person owns

The post-check flags every untracked file that matches a protected path. A file you created
yourself, such as an uncommitted `CLAUDE.local.md` or a folder `AGENTS.md`, therefore flags
`protected-path` after each modifying call. Commit it on the base branch (a commit on the task
branch still differs from the base), or gitignore it. The flag message tells the agent the same:
"commit it, gitignore it, or stop and ask if you did not create it. A person's own file: commit
it on the base branch". When the base branch has moved since the scope was approved, the message
adds that a person must re-run `aidlc scope`: after a rebase or merge from the base, the base's
own new commits look like changes on the task branch until you re-scope.

## The retry counter

The post hooks count runs of the one-command check, and the guard enforces the limit. What
counts, what resets and who resets are in [the retry limit](../checks/README.md#the-retry-limit);
the exact rules are in `core/hooks/README.md`.

- **The attempts record** is `attempts/<repo>-<hash8>/<branch>.json` under `AIDLC_HOME_DIR`
  (default `~/.aidlc`). A detached HEAD has its own record, so detaching never escapes the count.
  Updates hold a file lock, so parallel hooks lose no count.
- **It fails closed.** An unreadable record, or a record, lock or folder that is a symlink or not
  a regular file, counts as at the limit.
- **The decision log** gets a `check-attempts` record for each counted run, next to the usual
  `post-tool-check` record. At the limit the `post-tool-check` record carries `retry-limit`,
  unless another rule flagged the same call first.
- **Only hooks write it.** The sandbox denies `~/.aidlc` to agent shells. A person resets it with
  `aidlc attempts --reset`, which agent shells cannot run.

## What the guard leaves to others

The guard is pattern-based. It is not a shell. It deliberately leaves these to the sandbox and
to branch protection: ANSI-C escapes, brace expansion, variable indirection, interpreters running
code, and parsing differences between shells. The authoritative list is the "Deliberate limits"
section of `core/hooks/README.md`. Read it before you rely on the guard for anything new.

Anything the guard cannot parse asks a person. That is the reason for the next section.

> ⚠️ **Watch out:** `source .venv/bin/activate && ...` asks, and an ask is a deny when nobody is
> there. In unattended runs call `.venv/bin/python` directly.

## Limits

- Commands longer than 65,536 characters are denied.
- Analysis has a 0.5 second budget, checked inside the scanner. Nesting deeper than 40 levels is
  denied. Together with a short start-up this keeps a run well under one second.
- Post-check output larger than 5,000,000 characters is flagged as unscanned.
- Each hook script sets `sys.dont_write_bytecode`. A `__pycache__` folder in the repository
  would be flagged by the post-check and would pollute the diff.

## Environment variables

Read from `core/hooks/guard.py`, `core/hooks/post_check.py` and `core/hooks/claude_shim.py`.

| Variable | Effect |
|---|---|
| `AIDLC_UNATTENDED` | Any non-empty value except `0`, `false` or `no` turns every ask into deny |
| `AIDLC_HARNESS_FILE` | Harness data file; default is `harness.json` next to the script |
| `AIDLC_SCOPE` | `off` disables edit-scope enforcement; logged, and refused when unattended |
| `AIDLC_SCOPE_FILE` | Explicit scope file; ignored if it lives inside the repository |
| `AIDLC_HOME_DIR` | Base for scope files, the attempts record and the recorded framework entry; default `~/.aidlc` |
| `AIDLC_LOG_DIR` | Decision log directory; default `~/.aidlc/logs` |
| `AIDLC_BASE_REF` | Base the post-check diffs against; overrides the scope's recorded `base:` and `harness.base_branch` |

## Adding a rule

1. Change the source: the policy in `core/policy/permissions.yaml` for a pattern, or
   `core/hooks/guard.py` for a new kind of check. A policy change needs a design change.
2. Add fixtures: a case that must be denied and one that must still pass.
3. Render: `aidlc render --tool claude-code`. The harness `version` changes with the data.
4. Run the attack tests: `tests/unit/test_attacks_direct.py`, then `make harness-live` when a
   model is available.
5. Run `aidlc doctor`, see [doctor](doctor.md).

> 🎯 **What this means for you:** Prefer a deny rule in the policy over a new guard check. The
> policy renders into permissions, sandbox and guard together.

Guide: 3 step 5, 3.7.
