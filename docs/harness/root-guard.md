# The root guard: start Claude Code at the repository root

Claude Code loads a repository's `.claude/settings.json` only when the session starts at that
repository's root. Start it in a subdirectory, or work on the repository's files from another
folder, and none of its permissions, sandbox or hooks apply. This was tested on 2026-10-19: a file
write from a subdirectory went through unchecked
([check 7](../verification/2026-10-18-sandbox-wsl2.md#2026-10-19-check-7)).

A repository's own settings cannot fix this, because they are the part that does not load. The fix
belongs one level up, in **managed settings**: the file an organisation controls for every session
on a machine, which a developer and an agent cannot change.

## What it does

`core/managed/aidlc_root_guard.py` is a `PreToolUse` hook for every tool. It refuses a tool call
when the session's working directory, or the file or folder the tool names, is inside an aidlc
repository (a git root holding `.aidlc/config.yaml`) that is not the folder where the session
started. The refusal names the repository root to start from. Everywhere else it says nothing.

| Session started at | Works on | Result |
|---|---|---|
| `svc/` (the root) | `svc/src/app.py` | allowed; the repository's harness applies |
| `svc/src/` | anything | refused: start at `svc/` |
| `~/notes` | `svc/src/app.py` | refused: start at `svc/` |
| `~/other-repo` (no aidlc) | its own files | allowed; the guard has no view |

It fails closed: unreadable input exits 2, and `onFailure: block` blocks a crash or timeout.

**Limits.** It reads the working directory and the `file_path`, `notebook_path` and `path`
inputs. A shell command that reaches another repository by its own path (`cd /other && …`) is not
parsed. That repository's trusted CI still judges every change.

## Install it (the machine's administrator)

You need root, because managed settings and the guard must be files the developer cannot edit.

1. Copy the guard:

   ```bash
   sudo install -d -m 755 /etc/claude-code/hooks
   sudo install -m 644 core/managed/aidlc_root_guard.py /etc/claude-code/hooks/aidlc_root_guard.py
   ```

2. Add the hook entry from `core/managed/managed-settings.hooks.json` to
   `/etc/claude-code/managed-settings.json`. If the file already has a `hooks` key, add the
   `PreToolUse` entry to it rather than replacing it. This merges and shows the result before you
   install it:

   ```bash
   python3 - core/managed/managed-settings.hooks.json /etc/claude-code/managed-settings.json > /tmp/managed-settings.json <<'PY'
   import json, sys
   add = json.load(open(sys.argv[1]))["hooks"]["PreToolUse"]
   try:
       current = json.load(open(sys.argv[2]))
   except FileNotFoundError:
       current = {}
   current.setdefault("hooks", {}).setdefault("PreToolUse", [])
   current["hooks"]["PreToolUse"] = [e for e in current["hooks"]["PreToolUse"] if e not in add] + add
   print(json.dumps(current, indent=2))
   PY
   cat /tmp/managed-settings.json
   sudo install -m 644 /tmp/managed-settings.json /etc/claude-code/managed-settings.json
   ```

3. Check it: start `claude` in a subdirectory of an aidlc repository and ask it to read a file.
   The call is refused with "[aidlc root-guard] … start a new session in …".

A fleet distributes the same file through its device management, as it does the telemetry settings
([proposed platform changes](../observability/platform-patch.md)).
