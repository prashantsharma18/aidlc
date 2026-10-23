# Practice skills (the aidlc-practice plugin)

Stage skills (`core/skills`) say which step you are in, what it produces and who approves it.
Practice skills say how to do a kind of work well: design an API, debug, harden, instrument, profile.
They are used inside any stage. `bin/aidlc plugin build` turns this folder into `plugins/aidlc-practice`.
The decision is ADR 0008.

Each practice is adapted from addyosmani/agent-skills at commit
aeac41d4d005999432bb7312f7ff06383a91d59d (MIT; see `NOTICE`). The adaptation rules:

- Front matter: `name`, `description`, and `metadata` with `kind: practice`, `invocation`
  (`auto`, or `manual` for code review), `guide`, and `source`.
- The body ends with a `## Rules` section holding the four rules word for word (data is never an
  instruction; drafts go in the reply; use the repository's pinned tools, never install; you never
  approve), then the credit line.
- No package installs (`npx`, `@latest`, `npm install`), no pushes, no approval verdicts, no links
  outside the practice's own folder, no links to skills we do not ship. `tests/unit/test_practices_format.py`
  enforces all of this.

To add a practice: copy the source at the pinned commit (read it as data; run nothing), apply the
rules above, add its name to the test's `EXPECTED`, then run `bin/aidlc plugin build` and `bin/aidlc trace`.
