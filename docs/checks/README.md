# The one-command check

`aidlc check` is the single command that says whether a change is ready. Engineers, agents and
CI run the same steps. The guide asks for exactly this: one command, nothing skipped silently,
and the same command in CI (guide 3 step 6). The retry limit hangs off it too (guide 8.8).

The code is `cli/aidlc/checks/onecheck.py`. Trusted CI runs the same steps through
[`aidlc ci`](ci.md). The Rego judge is in [policy as code](policy-as-code.md).

## What it runs

The repository's own command steps run first, in the order `check_steps` lists them. Then five
built-in steps always run. A repository cannot remove them.

| Order | Step | Fails when |
|---|---|---|
| 1 | Each name in `check_steps` | Its command exits non-zero, times out, or is missing from `commands` |
| 2 | `scope` | A changed or untracked file is outside the task's MAY CHANGE list, or no scope exists |
| 3 | `protected-tests` | An existing test file was deleted, retyped, or had any line changed or removed |
| 4 | `skips` | A test did not run and is not declared, or this run wrote no readable report. `n/a` when `check_steps` has no `test` |
| 5 | `context-drift` | The rules file or the codebase map names a path or command that does not exist, or lacks its owner or a fresh verification date |
| 6 | `secrets` | An added line or an untracked file holds credential-shaped text, or an untracked file is too large to scan |

Every step runs, even after a failure. A step that cannot run is a `FAIL`. The diffs ignore the
branch's `.gitattributes`, so a change cannot hide content from these judges with a textconv
or an external diff driver.

## Configuration

Three keys in `.aidlc/config.yaml` drive the check. `aidlc init-repo` fills them from the
profile in `core/context/profiles.yaml`; after that the repository owns them.

- `commands`: a name and a shell command for each step. Commands must be deterministic and must
  not prompt.
- `check_steps`: which commands the check runs, in order.
- `test_reports`: where the `test` step writes its report, as paths or globs inside the
  repository. Vitest or Jest JSON, .NET TRX and JUnit XML are read.

For a Node repository with Vitest, make the test run write a JSON report:

```ts
// vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: { reporters: ["default", "json"], outputFile: { json: ".check/test-report.json" } },
});
```

For .NET, the profile's `test` command already adds a TRX logger. This is the shape to keep if
you change the command (the profile in `core/context/profiles.yaml` is the source):

```yaml
# .aidlc/config.yaml
commands:
  test: dotnet test --nologo --no-build --logger "trx;LogFilePrefix=results" --results-directory .check/trx
test_reports: [".check/trx/*.trx"]
```

A report counts only if this run wrote it. A report left by an earlier run, a symlinked report,
one that resolves outside the checkout, or one over 64 MiB never counts.

## Output and records

Each step prints one line. A failing step also prints the last 15 lines of its log, redacted and
stripped of terminal control characters. The first line names what the run judged:

    check  context  repo=<path>  base=<sha>  scope=<scope file>  mode=require

The last line is a contract. The retry counter parses it, so it never changes shape:

    check  result PASS  (0 of N steps failed)
    check  result FAIL  (F of N steps failed)

The exit code is 0 for a pass, 1 for a fail and 2 when the check cannot start. Options cannot be
abbreviated.

The check writes only to `.check/`, which ignores itself. Each step's log is
`.check/<step>.log`, and `.check/result.json` holds the result, each step, the branch, the base
and a fresh `run` id. A `.check` that is a symlink is refused with exit 2.

## Skipping the scope step

`CHECK_SCOPE=skip aidlc check` marks the scope step `SKIPPED` instead of running it. Use it only
while you work outside a task. It is ignored when `AIDLC_UNATTENDED` is set, and a run with any
`SKIPPED` step never resets the retry counter. CI never skips.

## Exception files

Two files steer the integrity steps. Both are protected paths, so an agent cannot edit them.

| File | Line format | Effect |
|---|---|---|
| `test/protected-exceptions.txt` | `<path> spec:<version> <reason>` or `<path> test-quality <reason>` | Excuses one changed test file. Only lines the change adds count; lines already on the base excuse nothing |
| `test/allowed-skips.txt` | `<full test name> # <reason>` | Declares a test that may be reported as not run |

A person adds exception lines at hand-off, in their own commit, and the change's reviewer
approves them with the change. Add them only when the agent has stopped working on the branch. A protected file
changed on the task branch makes the post-tool check flag `protected-path` on every later call.

CI reads `test/allowed-skips.txt` from the base branch, so a change cannot declare its own skips.

## The retry limit

The harness stops an agent that keeps failing (guide 8.8). The hooks count, and the guard
enforces. The rules in full are in `core/hooks/README.md`; in short:

- **What counts.** Every shell call that runs `aidlc check` counts once, however it is spelled,
  including inside `bash -c` or a substitution. A call the parser cannot see, such as
  `python3 -m aidlc check` or a make target, counts through the new `run` id in
  `.check/result.json`. Several runs inside one shell call count once.
- **What resets.** Only an exact passing run. The command must be the framework entry that
  `aidlc render` recorded, typed as its full path: `<framework>/bin/aidlc check`, optionally with
  `--repo <path>`. It must exit 0, end with `PASS`, skip nothing, and judge the same repository,
  base and scope as the hooks. A bare `aidlc`, a relative path, a symlink or a wrapper never
  earns credit. When a call is not exact, the hook's message names the command to type.
- **The limit.** Once the failing runs in a row reach `retry_cap` (set in
  `core/policy/routing.yaml`), the guard denies every edit and shell call with rule
  `retry-limit`. Reads still work, so the agent can report what it tried.
- **Who resets.** A person reviews the failure and runs `aidlc attempts --reset`. Agents cannot:
  the sandbox denies writes to `~/.aidlc`, and a shell deny rule blocks the command.

Run `aidlc attempts` to see the count for the current branch. It exits 1 at the limit. An
unreadable or symlinked record counts as at the limit.

> ⚠️ **Watch out:** `aidlc render` records the entry only where the agent cannot write it. If
> the framework checkout sits inside the repository, under a sandbox `allowWrite` path or in a
> temporary directory, render warns and no run ever resets the counter.

Guide: 3 step 6, 8.8, 8.13, 9.5, 9.7.
