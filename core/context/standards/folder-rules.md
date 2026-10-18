---
id: ctx-folder-rules
guide: ["2.6", "2.8 A5", "4.13"]
---
# Standard: folder rules

Rules that apply to one area load only when the agent works there, so they cost nothing elsewhere.

## Source format (tool-neutral, one area per file)
`.aidlc/rules/<name>.md`:

    ---
    paths: ["db/migrations/**"]
    description: Optional one line
    ---
    Never edit an existing migration; add a new one. (CI also checks this.)

`paths:` is required: a non-empty list of globs relative to the repository root.

## Rendering
`aidlc render --tool <tool>` writes the tool's path-scoped files; never edit the output.
- Claude Code: `.claude/rules/<name>.md` with `paths:` front matter.
- GitHub Copilot (extension point): `.github/instructions/<name>.instructions.md` with `applyTo:`.

## What belongs here
Conventions and traps specific to one area, such as a generated directory, a frozen legacy package,
or the migration rules. A rule every task needs belongs in `AGENTS.md`. A must-hold rule also needs
enforcement.
