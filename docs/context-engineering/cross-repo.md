# Context across repositories

- Work from a workspace folder (not a repository) holding the repositories for one change and a
  `WORKSPACE.md` (template `workspace`) that points to the coordination plan.
- Discovery and planning run read-only across the workspace, one explorer per repository.
- Building runs one session per repository, started in that repository, so its own rules file,
  harness and one-command check apply. Neighbours are read-only, enforced by the sandbox and the
  absence of write credentials, not by instruction.
- Each repository keeps its own rules. To have Claude Code load a neighbour's rules in a discovery
  session, start it with `--add-dir <neighbour>` and `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`.
- Contracts are pointed to at a version (a tag), never copied: a copy is a second truth that drifts.
- Organisation-level standards live once in this framework, pinned by each repository.

Guide: 2.11, 14.4.
