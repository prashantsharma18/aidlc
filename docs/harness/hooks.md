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
  error, which the tool treats as a block. The settings also set `onFailure: block`, so a crash
  or a timeout blocks too.

## The rules and their reasons

`core/hooks/README.md` lists every check. In short:

| Rule | Reason |
|---|---|
| Edits must stay inside the repository and inside the task scope | The task bundle approved on `main` defines what may change |
| Protected paths are always denied | The agent must not weaken the controls that judge it |
| Shell commands are matched against `shell_deny` after normalisation | Wrappers, substitutions and absolute paths must not hide `git push` |
| Piping into a shell is denied; a nested shell asks | The inner command cannot be judged |
| MCP tools are matched against `tool_deny` and `tool_ask` | Tracker writes need a person |
| External reach always asks | Retrieved text may be hostile |
| Post-check: secret-shaped output, writes outside scope, a changed or removed assertion, a disabled test or narrowed suite (`skipped-test`: `.skip`, `.only`, `[Fact(Skip=...)]`, `@Disabled` and similar) | The fast first line before trusted CI |

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
| `AIDLC_HOME_DIR` | Base for scope files; default `~/.aidlc` |
| `AIDLC_LOG_DIR` | Decision log directory; default `~/.aidlc/logs` |
| `AIDLC_BASE_REF` | Base branch the post-check diffs against; default `main` |

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
