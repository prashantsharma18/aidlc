# Plan 7: skills-first aidlc — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn aidlc into a portable skills package (like addyosmani/agent-skills) that engineers install in Claude Code, Copilot, Codex or Cursor, with the workspace working model built in and no Python harness.

**Architecture:** Skills, agents and templates are authored once under `skills/` and `agents/`; the Claude Code plugin points at them and other tools copy them. Gates move into the skills' text and the team's normal pull-request review and CI. The harness stays under the tag `harness-v1`.

**Tech Stack:** Markdown (Agent Skills format), one Python standard-library validation script, a GitHub Actions workflow.

**Spec:** `docs/design/2026-10-25-skills-first.md` (and `docs/design/2026-10-24-workspace-working-model.md` for the workspace model)

## Global Constraints

- Every skill follows the open format: a folder named like the skill, `SKILL.md` with YAML front matter (`name`, `description`), optional `assets/`. Descriptions say what the skill does and "Use when …".
- Keep the house style that made the skills good: Steps, Produces, Gate, Stop if, Common excuses, Red flags, Rules; "You draft; you never approve."
- No tool-specific instruction in a skill's body; tool specifics live in `docs/` quickstarts. A skill names commands only as "the repository's commands from AGENTS.md".
- No Python package, hooks, policy engine or generator in the main tree after Task 2. `scripts/validate.py` uses the standard library only.
- Credit: the practice skills keep their MIT notice and credit line.
- Commits use the noreply identity; nothing is pushed without the user's go-ahead.

## Review Focus

1. A skill that still names a removed command (`aidlc check`, `aidlc scope`, `approved-bundles.txt`, `aidlc ci`) → `validate.py` fails (Task 5 test).
2. A skill folder whose name differs from its `name:` field, or a `SKILL.md` without `description` → `validate.py` fails (Copilot and Codex refuse such skills).
3. A defect routed without a reproduction, or a change request without its original story → `aidlc-start` stops and asks (text check in Task 3).
4. A one-repository story → every story-level skill still allows the whole flow inside that repository.
5. The Claude Code plugin manifest points at folders that exist; `claude plugin validate` passes.

---

### Task 1: Inventory and the keep/park list

- [ ] List every file under `core/`, `cli/`, `plugins/`, `tests/`, `docs/`, `bin/`, `Makefile`, `.github/` and mark it **keep** (content), **move** (to the new layout), **park** (removed from the tree; available in `harness-v1`) or **rewrite**. Keep: stage skills, practice skills, agents, templates, operating-model and ADR docs. Park: `cli/`, `bin/`, `core/hooks`, `core/policy*`, `core/adapters`, `core/ci`, `core/managed`, `core/observability`, `core/schemas`, `core/context` (except the AGENTS.md and codebase-map templates), `tests/`, `Makefile`, the generated `plugins/`, harness docs.
- [ ] Write the list to `docs/archive/harness-v1.md` with one line on how to get any parked file back (`git show harness-v1:<path>`).

### Task 2: The new layout

- [ ] Create `skills/` from the generated `plugins/aidlc/skills/*` and `plugins/aidlc-practice/skills/*` (they already hold each `SKILL.md` with its `assets/`), `agents/` from `core/agents/*`, and `starter/` (empty for now).
- [ ] Rename `aidlc-build-slice` to `aidlc-build`; merge `aidlc-context-setup` and `aidlc-adopt` into `aidlc-onboard` (set up a repository or a workspace: AGENTS.md, the codebase map, the starter files, for a new or an existing repository).
- [ ] Replace `.claude-plugin/marketplace.json` with one plugin, `aidlc`, whose `plugin.json` names `skills/` and `agents/`.
- [ ] Remove the parked paths with `git rm`. Commit: `refactor: skills-first layout; the harness is parked under harness-v1`.

### Task 3: `aidlc-start` and the workspace model

- [ ] Write `skills/aidlc-start/SKILL.md` as designed in Plan 6b: the kind of work (new feature, defect, change request, incident follow-up), the scope (one repository or several, unsure counts as several), the two entry paths (no story yet, the story exists), never splitting a story, and the story index `stories/<KEY>/README.md` with the stage checklist and where each stage runs.
- [ ] Add the "Where this runs" paragraph to every stage skill (story level at the workspace root for a multi-repository story; part level inside the repository; a one-repository story runs entirely in that repository), the job sheet's PARTS table to `aidlc-design`'s coordination-plan asset, branch and PR naming to the part-level skills, repository-named criteria and the amendment's "re-plan" marking to `aidlc-specify`, and the existing-story check to `aidlc-intent`.

### Task 4: Simplify every skill for portability

- [ ] Remove every reference to the harness: `aidlc check` becomes "the repository's test and lint commands (AGENTS.md)"; `aidlc scope` and approval lines become "the plan is approved in its pull request (or by the tech lead in the story)"; "the person saves the draft" becomes "write the draft to `<path>` on the story branch; it is reviewed in the pull request".
- [ ] `aidlc-build`: the scope rule becomes "before handing off, list `git diff --name-only` against the bundle's MAY CHANGE; anything outside is a stop"; keep tests first, the three-attempt rule, never editing an existing assertion.
- [ ] `aidlc-verify`: reads the pull request's CI results (or the local test output when there is no CI) instead of `aidlc ci` records.
- [ ] `aidlc-review`: unchanged in spirit (three reviewer agents, dispositions, the code owner decides); the "CI's AI review" line points to the starter's optional AI-review workflow or Copilot code review.
- [ ] Keep each skill's excuses, red flags and rules.

### Task 5: The validator

- [ ] `scripts/validate.py` (standard library): every `skills/*/SKILL.md` has front matter with `name` equal to its folder, a `description` containing "Use when", the house sections, no removed command (Review Focus 1), and every asset it names exists; every `agents/*.md` has `name` and `description`; the plugin manifest's paths exist. Exit 1 with one line per problem.
- [ ] Write it test-first against small fixture folders (`scripts/test_validate.py`, `python3 -m unittest`).
- [ ] `.github/workflows/validate.yml` runs both on every pull request. Commit.

### Task 6: Starter files and quickstarts

- [ ] `starter/repo/`: `AGENTS.md` (template with the "How to work" behaviours), `.claude/settings.json` (deny reading `.env*`, `*.pem`, `*.key`, `secrets/**`; sandbox on; ask before `git push`), `.github/workflows/ci.yml` (runs the repository's commands from AGENTS.md), `CODEOWNERS` example, and an optional `.github/workflows/ai-review.yml` (Claude code review, needs an API key).
- [ ] `starter/workspace/`: `WORKSPACE.md` (repositories, owners, how work runs: start with `/aidlc-start`), `stories/README.md`, a read-only `.claude/settings.json` for the root.
- [ ] `docs/quickstart/claude-code.md` (marketplace add, plugin install, copy the starter files), `copilot.md` (copy `skills/` to `.github/skills` or `~/.copilot/skills`, agents to `.github/agents/*.agent.md`; works in VS Code agent mode, the CLI, the coding agent), `codex-cursor.md` (`.agents/skills`, `.cursor/skills`).
- [ ] `README.md` rewritten: what aidlc is, the flow in one diagram, install per tool, the skills list. `docs/operating-model.md`: the two levels, the routing table, the job sheet, the four review layers without the harness. ADR 0010 (skills-first) and ADR 0009 (the workspace model). Commit.

### Task 7: End to end on the demo workspace

- [ ] Re-baseline `~/work/shipment-tracking`: remove the rendered harness files (`.aidlc/hooks`, generated `.claude/settings.json`, `.aidlc/` config), copy the starter files, keep AGENTS.md and the codebase maps; move SHIP-1's story documents to `stories/SHIP-1/`.
- [ ] Install the plugin in Claude Code from this checkout (`claude plugin marketplace add ~/demos/aidlc`, `claude plugin install aidlc@aidlc`), not with `--plugin-dir`.
- [ ] Run a small new piece of work through it, chosen with the user (for example a defect "SHP-1003's page shows nothing when the carrier sends an inverted window; show a 'no estimate' note instead"): `aidlc-start` → its route → build → verify → review, up to a pull-request-ready branch. Record each step, its output and where it is kept.
- [ ] Copilot: copy `skills/` and `agents/` into the demo repositories' `.github/` and check in VS Code agent mode that the skills list and `aidlc-start` load (the user drives; Copilot CLI only if the user approves installing it). Codex or Cursor: install only with the user's approval; otherwise check the files against each tool's documented layout.
- [ ] Write `docs/verification/<date>-skills-first.md`.

### Task 8: Final review

- [ ] `python3 scripts/validate.py`, `python3 -m unittest scripts/test_validate.py`, `claude plugin validate .`; a fresh reviewer reads the whole branch; one fix pass; report.
