# Multi-repo foundations Implementation Plan (Plan 21: phase 2a of aidlc 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A story across several repositories keeps each fact in one place, with one owner. Each part pins the spec by
version and by the home repository's commit, and keeps a read-only copy of its own criteria, so its CI and reviewers
never need the home repository. Part status comes from the real merge state. A contract is a published, versioned
artifact that consumers pin exactly (the Spec Kit rule).

**Architecture:** Three standard-library scripts change or arrive:
- `starter/workspace/scripts/story_status.py` gains the drift check (home commit and criteria copy), the merge state
  (GitHub first, git otherwise) and `--write-gitignore`;
- `starter/repo/scripts/check_contract_version.py` (new) is the provider's contract check: a changed contract raises
  `info.version`, a breaking change (oasdiff) raises MAJOR, and `--publish-tag` names the tag the default branch
  creates;
- `starter/repo/scripts/check_contract_pin.py` (new) is the consumer's pin: each copy in `contracts/<provider>/`
  matches its `SOURCE` (offline in CI; `--online` checks the tag; `--update` moves the pin to a named tag).

Two starter workflows run the provider side (`contract-check.yml`, `contract-publish.yml`); the starter `ci.yml`
gains a `contract-pin` job. The workspace starter gets a `CODEOWNERS`. The skills, templates and one ADR (0022) say
where each fact lives and how parts pin.

**Tech Stack:** Python 3.12 standard library (`unittest`, `subprocess`, `hashlib`, `json`, `re`), git, the GitHub
CLI when present, GitHub Actions YAML, oasdiff 1.35.0 (release binary, in CI only), Markdown.

**Spec:** `docs/design/2026-11-19-aidlc-6-change-list.md`, section F and decisions D1–D9. Phase 2a is F1–F6 (F6 and
the local drift check designed additively), F9 (D5: the OpenAPI package; D9: oasdiff), F11, F13 and F14. Research
basis: GitHub Spec Kit's contract-driven development (one side owns the contract; consumers pin an exact version or
keep a read-only copy whose README names its source, path and immutable revision; changes are proposed at the
source; never silently follow latest) and Matt Pocock's Home Repo (what is true of one repository stays there; shared
facts and system-wide decisions live in the home repository).

Branch: `docs/plan-21-multirepo-foundations` (already checked out; this plan is its first commit). Base: local `main`
at `2ce7deb`, aidlc 5.0.0 (unreleased).

## Decisions this plan makes

| Question | Decision | Why |
|---|---|---|
| Where a part's merge state comes from (F6) | GitHub first: the part's newest code pull request (title `[<KEY>] part <n> of <m>:` or `…, revision <r>:`), when the repository has a GitHub remote and `gh` answers. Otherwise git: the default branch's copy of the part index (`origin/<default>` when it exists, else local `main` or `master`), read with `git show` | The merged row reaches the default branch only through the part's merge (ADR 0015, `aidlc-review` step 8), so the default branch's copy holds for merge commits, squash and rebase alike, and after the branch is deleted |
| `git merge-base --is-ancestor` on the part's branch, as the brief suggested | Not the merge signal. It is used where it is exact: to check that a pinned home commit is on the home repository's default branch | A branch with no commits of its own is an ancestor of main (false "merged"); a squash or rebase merge, GitHub's common modes, never is (false "not merged") |
| The hand-marked `merged` row (F6 says remove it) | Kept. The script compares it with the real state and reports a disagreement as a need, which blocks the release | Removing it changes pinned assertions; see "Needs the owner's decision" |
| The pin format (F4) | `spec v<n> @ <commit>` in PINS, for a part of a story across several repositories. Only the spec carries the commit. A contract is pinned by version in PINS, and by tag, commit and sha256 in the consumer's `SOURCE` | The spec lives in the home repository; the contract's identity is its published tag |
| Where the drift check lives | Inside `story_status.py`, which already reads every part. It runs only when the workspace root is itself a git repository (the home repository); a plain folder keeps today's checks | No new script to copy or protect (`Edit(/scripts/story_status.py)` is already denied). The existing tests build plain folders, so they keep their exact `needs` |
| How a criteria copy is compared (F5) | Every copied line (below its first `## Acceptance criteria`, `## Edge cases` or `## Non-goals` heading; whitespace collapsed) must be a line of the spec at the SOURCE commit, and that commit must match the spec pin | Catches an edited or stale copy mechanically. Whether the copy holds all of the part's criteria stays the tech lead's judgement at plan approval |
| Where the copy lives | `plans/<KEY>/criteria.md`, beside the part index (`plans/<KEY>/part-<n>/criteria.md` for a second part) | Exempt from the slice check's scope like every story document; the part's CI checks out its own repository only |
| The `.gitignore` generator (F14) | `story_status.py --write-gitignore`; the story key becomes optional when the flag is given | The workspace already copies and protects this one script, and its test file exists. A separate script would need its own copy step and deny rule |
| The contract scripts | Two: `check_contract_version.py` (provider) and `check_contract_pin.py` (consumer, which imports `info_version` from the first, as `check_plan.py` imports `check_slice.py`) | Each side copies what it needs. Both names match the existing deny `Edit(/scripts/check_*.py)`, so a session cannot edit them |
| How oasdiff is installed (D9) | The release binary `oasdiff_1.35.0_linux_amd64.tar.gz` (published 2026-10-28, 23 days old), checked with `sha256sum -c` against `a8023002fcb2eaa7f5758148a9303cb63d33b939886df312268bc0fc7b939140` | `oasdiff/oasdiff-action@v0.1.21` builds its image at run time `FROM tufin/oasdiff:v1.35.0` (a tag, not a digest), and its `breaking` action uploads both specs to oasdiff.com by default (`review: true`) and sends telemetry. The Docker image's digest could not be verified from here |
| What the provider compares against | The highest `api-v<MAJOR.MINOR.PATCH>` tag in the clone (the last published version), not the pull request's base branch | Consumers pin published versions; a change merged but not yet tagged is still compared with what consumers have |
| The slice check and a pin move | No change to `check_slice.py`. Moving a pin is a slice whose MAY CHANGE names `contracts/<provider>/**`; other slices may name `contracts/**` in MUST NOT. Three new tests pin that behaviour | The scope check already does this; a pin move outside an approved bundle is reported as out of scope |
| The plan check and the criteria copy | `check_plan.py` unchanged; `story_status.py` reports a part with no copy | `scripts/test_check_plan.py:95-96` asserts the exact problem list for a part; a new problem there would change it |
| Tag protection | Documented in `contract-publish.yml` and ADR 0022, not set up | A ruleset on `api-v*` needs a public repository on GitHub Free, or a paid plan (D6). The consumer's `--online` check reports a moved tag either way |
| The plan pull request's title | `[<KEY>] part <n> of <m>, plan v<n>: <what>` (in `aidlc-plan`'s Gate) | The GitHub merge state reads code pull requests only; this title never matches `part <n> of <m>:` |
| "Contracts by version, never by copy" in `WORKSPACE.md` | Reworded: by version, at the published tag; a consumer's copy is read-only with its `SOURCE` | The Spec Kit rule allows a read-only copy that names its source; no test pins the old sentence |
| ADR | One: 0022, Proposed, written first (Task 1) | It changes where approved documents live and adds Decision 2's second pull request (amends ADRs 0015 and 0020) |
| Version | None. aidlc stays 5.0.0 | Phase 2 is not finished (2b remains), and `scripts/test_one_plugin.py:100` pins 5.0.0 |

## Global Constraints

- Python 3.12 standard library only. No new dependency in the framework. oasdiff runs only in the adopter's CI, at a
  pinned version and checksum (decision D9).
- Never change an existing test assertion. The current suite (548 tests) stays green after every task. New tests go
  in new files (`scripts/test_multirepo.py`, `scripts/test_check_contract.py`) or in new test classes appended to
  existing files, above their `if __name__ == "__main__":` line.
- Skills keep their sections. No tool-specific syntax in a skill (`/aidlc:`, `$ARGUMENTS`, `${CLAUDE_…}`). A skill
  never writes a backticked `scripts/<file>` on its own (the validator resolves it inside the skill folder); name a
  command in full (`python3 scripts/story_status.py --write-gitignore`) or by its role ("the contract pin command
  named in its AGENTS.md").
- No new "Load the `<name>` skill" command in any stage skill: `scripts/test_loads.py` pins the table exactly.
- Never write the word "pointer" in `starter/workspace/stories/README.md`, `starter/workspace/WORKSPACE.md` or
  `skills/aidlc-onboard/assets/workspace.md`: `scripts/test_routes.py:92` asserts it is absent.
- Templates under `skills/aidlc-*/assets/`: a placeholder outside a code block is written `{{…}}`; FIELD lines sit in
  a ```` ```text ```` fence; a document a person approves opens with `## For the reviewer`.
- Every `uses:` in a workflow is pinned to a 40-character commit SHA. A `run:` block never contains `${{ }}`; values
  reach the shell through `env:`.
- Commits: stage explicit paths (never `git add -A`). The author email is
  `6386481+prashantsharma18@users.noreply.github.com`. End each message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- After every task, run `python3 scripts/validate.py` and `python3 -m unittest discover -s scripts -p 'test_*.py'`.
  Both must pass.

## Review Focus

1. **A squash-merged part, or one whose branch was deleted after the merge.** It must still read as merged, and a
   fresh branch with no commits must not. The git signal reads the default branch's copy of the part index, never the
   branch. Task 3's `test_the_default_branchs_index_is_the_git_merge_state` builds a repository with no part branch
   at all; `test_a_merged_row_marked_on_a_branch_is_reported` marks merged on an unmerged branch.
2. **The tests must never reach the network or a parent repository.** A part folder inside the home repository, or a
   temporary folder inside some checkout, must not be read as the part's own repository, and only a GitHub remote may
   call `gh`. `own_repository()` guards both. Task 3's `test_a_folder_with_no_committed_index_adds_nothing`,
   `test_a_remote_that_is_not_github_never_calls_gh` and `test_no_github_reads_only_git`; every existing
   `test_story_status.py` assertion still passes unchanged.
3. **A hostile pull request on the provider.** Its contract may hold an external `$ref` (server-side request
   forgery from the runner), or the pull request may weaken the check script. oasdiff runs with
   `--allow-external-refs=false`, and CI runs the base branch's copy of the script. Task 5's
   `test_an_additive_change_with_a_new_minor_is_clean` asserts the exact oasdiff arguments; Task 7's
   `test_the_check_runs_the_base_branchs_script_read_only` asserts the base-branch copy and no write permission.
4. **A published version that moves, or a pin that follows "latest".** Task 6's `test_a_moved_tag_is_found_online`,
   `test_update_never_follows_latest` and `test_an_unpublished_tag_cannot_be_fetched`.
5. **A spec edited in place without a new version, or a part pinned to a draft commit.** Task 2's
   `test_a_spec_changed_since_the_pin_needs_a_re_plan` and `test_a_pin_off_the_default_branch_is_reported`; and
   `test_a_raised_version_is_one_re_plan_not_two` keeps the report to one line when the version did rise.

Known limits, stated in ADR 0022 and the scripts' docstrings: a criteria copy that leaves out one of the part's
criteria is not detected (the tech lead judges it with the plan); the GitHub merge state reads the newest 100 pull
requests whose title names the key; `gh` needs to be signed in; a workspace root that is not under git gets no
home-commit or criteria checks; `info_version()` reads JSON and block-style YAML, not flow-style YAML.

---

### Task 1: ADR 0022 and decision D9 (Proposed)

**Files:**
- Create: `docs/adr/0022-one-owner-per-fact-and-pinned-parts.md`
- Modify: `docs/design/2026-11-19-aidlc-6-change-list.md` (one row, D9, after D8)
- Create: `scripts/test_multirepo.py`

**Interfaces:**
- Produces: `scripts/test_multirepo.py` with `ROOT`, `VANISHING`, `read(rel)`, `flat(rel)`, `skill(name)` and
  `gate(name)`, and `pinned_uses`, `run_blocks` imported from `scripts/test_gates_hold.py`. Later tasks append
  classes above its `if __name__` line.

- [ ] **Step 1: Branch and identity**

```bash
cd /home/psharma/demos/aidlc
git branch --show-current   # must print docs/plan-21-multirepo-foundations
git config user.email       # must print 6386481+prashantsharma18@users.noreply.github.com
```

- [ ] **Step 2: Write the failing tests**

Create `scripts/test_multirepo.py`:

```python
"""Plan 21: a story's facts have one owner, and parts pin by version and commit (ADR 0022). The skills, templates,
starters and workflows say so in the same words."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gates_hold import pinned_uses, run_blocks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VANISHING = re.compile(r"<[A-Za-z][^<>\n]*>")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(read(rel).split())


def skill(name: str) -> str:
    return flat(f"skills/{name}/SKILL.md")


def gate(name: str) -> str:
    return " ".join(read(f"skills/{name}/SKILL.md").split("## Gate", 1)[1].split("\n## ", 1)[0].split())


class AdrTest(unittest.TestCase):
    """The decision is recorded before the gates change."""

    def test_adr_0022_is_proposed_with_a_decider(self):
        text = read("docs/adr/0022-one-owner-per-fact-and-pinned-parts.md")
        self.assertRegex(text, r"Status: (Proposed|Accepted)")
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = " ".join(text.split())
        for phrase in ("Each fact has one owner, and only the owner changes it", "`spec v<n> @ <commit>`",
                       "`plans/<KEY>/criteria.md`", "`api-v<info.version>`", "Code that ships together goes in one repository"):
            self.assertIn(phrase, body, phrase)

    def test_the_change_list_records_d9(self):
        self.assertRegex(read("docs/design/2026-11-19-aidlc-6-change-list.md"), r"(?m)^\| D9 \| \*\*oasdiff")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run them to see them fail**

Run: `python3 -m unittest scripts.test_multirepo -v`
Expected: ERROR in `test_adr_0022_is_proposed_with_a_decider` (file not found) and FAIL in
`test_the_change_list_records_d9`.

- [ ] **Step 4: Write the ADR and the decision**

Create `docs/adr/0022-one-owner-per-fact-and-pinned-parts.md`:

```markdown
# 0022 · A story's facts have one owner; parts pin by version and commit

Status: Proposed (2026-11-20). · Decider: Prashant Sharma (framework owner)
Plan: `docs/plans/2026-11-20-plan-21-multirepo-foundations.md` · Change list: F1–F6, F9, F11, F13, F14; D5, D9 ·
Amends: ADR 0015 (where a story's documents live; how parts pin), ADR 0020 (Decision 2 across repositories)

## Context
A story across several repositories kept its shared documents at the workspace root and each part in its repository,
but nothing said which copy of a fact was the original. Child bundles cited `plans/SHIP-1/spec.md` after the spec
moved (P9). Part status came from rows people marked by hand, and the release check read whatever branch each clone
had checked out (P7). The contract was pinned by a code comment, and a tag was cut before review (P8). A child's CI
and AI review could not see the criteria, which lived in another repository (P10, P12).

## Decision
- Code that ships together goes in one repository. A workspace is for repositories that must stay separate:
  different owners, release cycles or runtimes.
- Each fact has one owner, and only the owner changes it. The home repository (the workspace root, under git) holds
  the story's index, intent, spec, design note, ADR drafts, contract draft, coordination plan, status, release records
  and incidents. Each part's repository holds its plan, bundles, criteria copy, progress notes, evidence, pull request
  description, review record, its own ADRs and its code. The provider holds the published contract.
- ADRs by scope. One that governs one repository moves to that repository's `docs/adr/`. One across repositories stays
  in the home repository's `docs/adr/`, and each affected repository gets a one-line ADR that links it at a commit.
  Drafts are named `<KEY>-adr-<n>.md`.
- A part pins the spec by version and by home commit: `spec v<n> @ <commit>`. Nothing under `stories/<KEY>/` is
  moved or renamed once a part pins it.
- Each part keeps a read-only copy of its own criteria, edge cases and non-goals in `plans/<KEY>/criteria.md`, under a
  SOURCE line naming the home repository, the spec's path and the commit. Its CI and its reviewers read the copy.
- `story_status.py` takes a part's merge state from its newest code pull request on GitHub when it can, else from the
  default branch's copy of the part index, and reports a hand-marked merged row that disagrees. It reports "re-plan"
  for a pin older than the story's spec, by version or by home commit, and reports a criteria copy that differs from
  the spec at its commit.
- A contract is a versioned artifact (the Spec Kit rule, D5). The provider owns the OpenAPI file its AGENTS.md names,
  and its default branch publishes each version as the tag `api-v<info.version>`. Its pull requests fail when the
  contract changed without a new version, or broke compatibility (oasdiff, D9) without a new MAJOR. Each consumer
  keeps a read-only copy with a SOURCE file (repository, tag, commit, path, sha256), checked offline in its CI, and
  moves it only to a named, published tag, in a planned slice.
- Decision 2 across repositories is the home design pull request, then each part's plan pull request.
- Tracker links are GitHub permalinks at a commit.
- The home repository's CODEOWNERS gives `stories/**` to the leads, and the runtime environment (compose files, flags)
  to its named owner. Its `.gitignore` is generated from the repository table in `WORKSPACE.md`.

## Consequences
- The merged row stays, marked by hand in the part's final commit (ADR 0015). The status command now checks it
  against the real merge state instead of trusting it.
- `git merge-base --is-ancestor` on the part's branch is not the merge signal: a branch with no commits of its own is
  an ancestor, and a squash or rebase merge never is. The default branch's copy of the part index holds for every merge
  method; the same check confirms that a pinned home commit is on the home repository's default branch.
- The home-commit and criteria checks run only when the workspace root is a git repository. A plain folder keeps
  today's version checks.
- A consumer's copy is a file in its own repository: its CI never needs the provider or the home repository.
- Not yet: a required story-gate status on child pull requests, the integration check before the last part merges,
  and GitHub App tokens per role (change list F7, F8, F10: phase 2b).
- Protecting `api-v*` tags needs a ruleset: a public repository on GitHub Free, or a paid plan. Without one, the
  consumers' online pin check still reports a tag that moved.
```

In `docs/design/2026-11-19-aidlc-6-change-list.md`, add this row to the decisions table, on the line after the row
that starts `| D8 | **Yes.**`:

```markdown
| D9 | **oasdiff for the provider's contract diff** (2026-11-20). | F9's "diff tool: ask" is answered. The provider's `contract-check` runs `oasdiff breaking --fail-on ERR --allow-external-refs=false` against the last published tag. It uses the release binary at a pinned version, checked against its published sha256: no action image built at run time, no account, and no upload of the contract. |
```

- [ ] **Step 5: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_multirepo -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS. The validator reports 0 problems; the suite is 550 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add docs/adr/0022-one-owner-per-fact-and-pinned-parts.md docs/design/2026-11-19-aidlc-6-change-list.md scripts/test_multirepo.py
git commit -m "docs(adr): 0022 a story's facts have one owner; parts pin by version and commit (proposed); D9 oasdiff" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: `story_status.py`: the home commit and the criteria copy (F4, F5, drift check)

**Files:**
- Modify: `starter/workspace/scripts/story_status.py`
- Test: `scripts/test_story_status.py` (add `import subprocess`; new helpers `run_git`, `criteria`, `Home`; new
  classes `HomeCommitTest`, `CriteriaCopyTest`)

**Interfaces:**
- Consumes: `items`, `VERSION`, `parse_versions`, `as_tuple`, `git`, `read`, `part_index` from the script.
- Produces (used by Tasks 3 and 4):
  - `AT_COMMIT`, `SOURCE_LINE` (module constants)
  - `without_commit(item: str) -> str`
  - `parse_commits(text: str) -> dict[str, str]`
  - `own_repository(folder: Path) -> bool`
  - `default_ref(folder: Path) -> str | None`
  - `copied_lines(text: str) -> list[str]`
  - `criteria_needs(workspace: Path, index: Path, commit: str | None) -> list[str]`
  - `drift_needs(workspace: Path, key: str, index: Path, pins_text: str, needs: list[str], covered: bool) -> list[str]`
  - In the tests: `run_git(folder, *args) -> str`, `criteria(root, repo, commit, lines=COPIED, source=True)`,
    `Home(root, current=..., extra=...)` with `.first`, `.commit(message, files) -> str`, `.status() -> dict`.

- [ ] **Step 1: Write the failing tests**

In `scripts/test_story_status.py`, change the import lines `import io` / `import sys` to:

```python
import io
import subprocess
import sys
```

Then append above `if __name__ == "__main__":`:

```python
# Plan 21: pins name the home commit, and each part keeps a read-only copy of its criteria (ADR 0022)

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null"]
SPEC = ("# SHIP-1 · Track shipments · specification\n\nVersion: v1\n\n## Scope and non-goals\n"
        "Non-goals: carrier rates\n\n## Acceptance criteria\nAC1 the API returns the shipment's status\n"
        "    Given a shipment in transit\n    When its status is asked for\n    Then 200 with \"in transit\"\n")
COPIED = ("AC1 the API returns the shipment's status", "Given a shipment in transit")


def run_git(folder: Path, *args: str) -> str:
    return subprocess.run(GIT + ["-C", str(folder), *args], check=True, capture_output=True, text=True).stdout.strip()


def criteria(root: Path, repo: str, commit: str, lines=COPIED, source: bool = True) -> None:
    head = f"```text\nSOURCE     home stories/SHIP-1/spec.md @ {commit} (spec v1)\n```\n\n" if source else ""
    text = f"# SHIP-1 · part · acceptance criteria (read-only copy)\n\n{head}## Acceptance criteria\n" + "\n".join(lines)
    (root / repo / "plans" / "SHIP-1" / "criteria.md").write_text(text + "\n", encoding="utf-8")


class Home:
    """A workspace root that is itself a git repository (the home repository): SHIP-1's documents on main."""

    def __init__(self, root: Path, current: str = "spec v1 · contract tracking-api v1", extra: str = ""):
        self.root = root
        story(root, current=current, extra=extra)
        (root / "stories" / "SHIP-1" / "spec.md").write_text(SPEC, encoding="utf-8")
        run_git(root, "init", "-q", "-b", "main")
        self.first = self.commit("spec v1")

    def commit(self, message: str, files: dict[str, str] | None = None) -> str:
        for rel, text in (files or {}).items():
            (self.root / rel).write_text(text, encoding="utf-8")
        run_git(self.root, "add", "stories")
        run_git(self.root, "commit", "-q", "--allow-empty", "-m", message)
        return run_git(self.root, "rev-parse", "HEAD")

    def status(self) -> dict:
        return {r.repository: r for r in story_status.story_status(self.root, "SHIP-1")}


class HomeCommitTest(unittest.TestCase):
    """F4: a part pins the spec by version and by the home commit; the drift check reads the home repository."""

    def home(self, **kwargs) -> Home:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Home(Path(tmp.name), **kwargs)

    def pinned(self, home: Home, commit: str, with_criteria: bool = True) -> None:
        part(home.root, "shipments-api", pins=f"spec v1 @ {commit} · plan v1 · contract tracking-api v1")
        part(home.root, "web-portal", pins=f"spec v1 @ {commit} · plan v1 · contract tracking-api v1")
        if with_criteria:
            criteria(home.root, "shipments-api", commit)
            criteria(home.root, "web-portal", commit)

    def test_a_pin_with_a_commit_is_parsed(self):
        text = "spec v2 @ 1A2B3C4 · plan v1 · contract tracking-api v2.1.0"
        self.assertEqual(story_status.parse_versions(text), {"spec": 2, "plan": 1, "contract tracking-api": (2, 1, 0)})
        self.assertEqual(story_status.parse_commits(text), {"spec": "1a2b3c4"})
        self.assertEqual(story_status.unread_items(text), [])

    def test_without_a_home_repository_a_commit_pin_adds_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", pins="spec v1 @ 1a2b3c4 · plan v1 · contract tracking-api v1")
            part(root, "web-portal")
            rows = {r.repository: r for r in story_status.story_status(root, "SHIP-1")}
        self.assertEqual(rows["shipments-api"].needs, [])

    def test_a_pin_at_the_current_home_commit_is_clean(self):
        home = self.home()
        self.pinned(home, home.first)
        self.assertEqual(home.status()["shipments-api"].needs, [])

    def test_a_pin_without_a_home_commit_is_reported(self):
        home = self.home()
        self.pinned(home, home.first)
        part_dir = home.root / "web-portal" / "plans" / "SHIP-1"
        (part_dir / "README.md").write_text((part_dir / "README.md").read_text(encoding="utf-8").replace(
            f" @ {home.first}", ""), encoding="utf-8")
        self.assertIn("the spec pin names no home commit (spec v<n> @ <commit>)", home.status()["web-portal"].needs)

    def test_a_spec_changed_since_the_pin_needs_a_re_plan(self):
        home = self.home()
        self.pinned(home, home.first)
        home.commit("edit the spec in place", {"stories/SHIP-1/spec.md": SPEC + "AC2 the portal shows it\n"})
        self.assertIn(f"re-plan: stories/SHIP-1/spec.md changed on main since {home.first[:7]}",
                      home.status()["shipments-api"].needs)

    def test_a_raised_version_is_one_re_plan_not_two(self):
        home = self.home(current="spec v2 · contract tracking-api v1")
        self.pinned(home, home.first)
        home.commit("spec v2", {"stories/SHIP-1/spec.md": SPEC.replace("v1", "v2") + "AC2 the portal shows it\n"})
        needs = home.status()["shipments-api"].needs
        self.assertIn("re-plan: spec v1 < v2", needs)
        self.assertFalse(any("changed on main" in n for n in needs), needs)

    def test_an_unaffected_record_clears_the_commit_re_plan(self):
        extra = "UNAFFECTED shipments-api spec v1: only the portal changes, Ana (tech lead), 2026-11-20"
        home = self.home(extra=extra)
        self.pinned(home, home.first)
        home.commit("edit the spec in place", {"stories/SHIP-1/spec.md": SPEC + "AC2 the portal shows it\n"})
        self.assertFalse(any("changed on main" in n for n in home.status()["shipments-api"].needs))

    def test_a_pin_off_the_default_branch_is_reported(self):
        home = self.home()
        run_git(home.root, "switch", "-q", "-c", "draft")
        draft = home.commit("an unapproved spec", {"stories/SHIP-1/spec.md": SPEC + "AC2 draft\n"})
        run_git(home.root, "switch", "-q", "main")
        self.pinned(home, draft, with_criteria=False)
        criteria(home.root, "shipments-api", draft)
        self.assertIn(f"pinned home commit {draft[:7]} is not on the home repository's main",
                      home.status()["shipments-api"].needs)

    def test_an_unknown_home_commit_is_reported(self):
        home = self.home()
        self.pinned(home, "deadbee")
        self.assertEqual(home.status()["shipments-api"].needs,
                         ["pinned home commit deadbee not found: run git fetch in the home repository"])


class CriteriaCopyTest(unittest.TestCase):
    """F5: each part's read-only copy of its criteria matches the home spec at the commit it names."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Home(Path(tmp.name))
        pins = f"spec v1 @ {self.home.first} · plan v1 · contract tracking-api v1"
        part(self.home.root, "shipments-api", pins=pins)
        part(self.home.root, "web-portal", pins=pins)
        criteria(self.home.root, "web-portal", self.home.first)

    def needs(self) -> list[str]:
        return self.home.status()["shipments-api"].needs

    def test_a_missing_copy_is_reported(self):
        self.assertEqual(self.needs(), ["no criteria.md beside the part index (the part's read-only copy of its "
                                        "criteria, ADR 0022)"])

    def test_an_edited_copy_is_reported(self):
        criteria(self.home.root, "shipments-api", self.home.first,
                 lines=("AC1 the API returns the shipment's status within 1 second",))
        self.assertEqual(self.needs(), [f"criteria.md differs from stories/SHIP-1/spec.md at {self.home.first[:7]}: "
                                        "AC1 the API returns the shipment's status within 1 second"])

    def test_a_copy_of_another_commit_is_reported(self):
        later = self.home.commit("the index moves on", {"stories/SHIP-1/coordination-plan.md": PLAN + "\n"})
        part_dir = self.home.root / "shipments-api" / "plans" / "SHIP-1"
        (part_dir / "README.md").write_text((part_dir / "README.md").read_text(encoding="utf-8").replace(
            f"spec v1 @ {self.home.first}", f"spec v1 @ {later}"), encoding="utf-8")
        criteria(self.home.root, "shipments-api", self.home.first)
        self.assertEqual(self.needs(), [f"criteria.md copies {self.home.first[:7]}, but the spec pin names {later[:7]}"])

    def test_a_copy_without_a_source_line_is_reported(self):
        criteria(self.home.root, "shipments-api", self.home.first, source=False)
        self.assertEqual(self.needs(), ["criteria.md has no SOURCE line naming the home repository, the spec's path "
                                        "and its commit"])

    def test_only_the_copied_lines_are_compared(self):
        text = ("# x\n```text\nSOURCE     home stories/SHIP-1/spec.md @ abc1234\n```\n## Acceptance criteria\n"
                "AC1  a   b\n\n```text\n## Non-goals\nNon-goals: {{x}}\nNon-goals: rates\n")
        self.assertEqual(story_status.copied_lines(text), ["AC1 a b", "Non-goals: rates"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_story_status -v`
Expected: the 31 existing tests pass; 13 of the 14 new ones fail or error (`parse_commits` and `copied_lines` do
not exist; "spec v1 @ <commit>" is not understood). `test_an_unaffected_record_clears_the_commit_re_plan` passes
already, because it asserts an absence; it guards the UNAFFECTED rule once the check exists.

- [ ] **Step 3: Add the drift check**

Make these replacements in `starter/workspace/scripts/story_status.py`, in order. Each "Replace" text occurs once.

1. Replace:

```python
Exits 2 when the story's index or coordination plan is missing. Standard library only."""
```

with:

```python
Exits 2 when the story's index or coordination plan is missing. Standard library only.

When the workspace root is itself a git repository (the home repository, ADR 0022), each part's spec pin also names a
home commit, `spec v<n> @ <commit>`: it must be on the home repository's default branch, and the story's spec must not
have changed since it. Each part keeps a read-only copy of its criteria beside its index, plans/<KEY>/criteria.md,
whose SOURCE line names the commit it copies; every copied line must be in the spec at that commit."""
```

2. Replace:

```python
UNAFFECTED = re.compile(r"^UNAFFECTED\s+([A-Za-z0-9._/-]+)\s+spec\s+v(\d+)\s*:", re.I)
```

with:

```python
UNAFFECTED = re.compile(r"^UNAFFECTED\s+([A-Za-z0-9._/-]+)\s+spec\s+v(\d+)\s*:", re.I)
AT_COMMIT = re.compile(r"\s*@\s*([0-9a-fA-F]{7,40})$")
SOURCE_LINE = re.compile(r"^SOURCE\s+(\S+)\s+(\S+)\s+@\s+([0-9a-fA-F]{7,40})\b", re.M)
```

3. Replace:

```python
        m = VERSION.match(item.lower())
```

with:

```python
        m = VERSION.match(without_commit(item).lower())
```

4. Replace:

```python
def unread_items(text: str) -> list[str]:
    return [item for item in items(text) if not VERSION.match(item.lower())]
```

with:

```python
def unread_items(text: str) -> list[str]:
    return [item for item in items(text) if not VERSION.match(without_commit(item).lower())]


def without_commit(item: str) -> str:
    """'spec v2 @ 1a2b3c4' -> 'spec v2': the version part of a pin that also names its home commit."""
    return AT_COMMIT.sub("", item)


def parse_commits(text: str) -> dict[str, str]:
    """'spec v2 @ 1A2B3C4 · plan v1' -> {'spec': '1a2b3c4'}: the home commit each pin names, when it names one."""
    commits = {}
    for item in items(text):
        at, version = AT_COMMIT.search(item), VERSION.match(without_commit(item).lower())
        if at and version:
            commits[version.group(1)] = at.group(1).lower()
    return commits
```

5. Replace:

```python
            needs.append(f"pins {name}, which the story no longer lists")
    return PartStatus(number, repository, reached, pins_text or "-", needs)
```

with:

```python
            needs.append(f"pins {name}, which the story no longer lists")
    spec_now = as_tuple(current["spec"])[0] if "spec" in current else 0
    covered = spec_now > 0 and unaffected.get(repository, 0) >= spec_now
    needs += drift_needs(workspace, key, index, pins_text, needs, covered)
    return PartStatus(number, repository, reached, pins_text or "-", needs)
```

6. Replace:

```python
def story_current(workspace: Path, key: str)
```

with:

````python
def own_repository(folder: Path) -> bool:
    """True when the folder is the top of its own git repository, not a folder inside another one."""
    top = git(folder, "rev-parse", "--show-toplevel")
    return top is not None and Path(top).resolve() == folder.resolve()


def default_ref(folder: Path) -> str | None:
    """The ref that stands for the default branch: origin's (the freshest after a fetch), else a local main or master."""
    remote = git(folder, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if remote:
        return remote
    return next((b for b in ("main", "master") if git(folder, "rev-parse", "--verify", "--quiet", f"refs/heads/{b}")),
                None)


def copied_lines(text: str) -> list[str]:
    """The lines criteria.md copies from the spec: everything below its first criteria, edge-case or non-goals
    heading, except headings, fences, blank lines and template placeholders; whitespace runs collapsed."""
    lines, inside = [], False
    for line in text.splitlines():
        if re.match(r"^##\s+(Acceptance criteria|Edge cases|Non-goals)", line):
            inside = True
            continue
        flat = " ".join(line.split())
        if inside and flat and not flat.startswith(("#", "```")) and "{{" not in flat:
            lines.append(flat)
    return lines


def criteria_needs(workspace: Path, index: Path, commit: str | None) -> list[str]:
    """F5: the part's read-only copy of its criteria matches the home spec at the commit it names."""
    copy = index.parent / "criteria.md"
    if not copy.is_file():
        return ["no criteria.md beside the part index (the part's read-only copy of its criteria, ADR 0022)"]
    text = read(copy)
    source = SOURCE_LINE.search(text)
    if not source:
        return ["criteria.md has no SOURCE line naming the home repository, the spec's path and its commit"]
    path, at = source.group(2), source.group(3).lower()
    needs = []
    if commit and not (commit.startswith(at) or at.startswith(commit)):
        needs.append(f"criteria.md copies {at[:7]}, but the spec pin names {commit[:7]}")
    spec = git(workspace, "show", f"{at}:{path}")
    if spec is None:
        return needs + [f"criteria.md: {path} at {at[:7]} cannot be read in the home repository"]
    spec_lines = {" ".join(line.split()) for line in spec.splitlines()}
    needs += [f"criteria.md differs from {path} at {at[:7]}: {line[:80]}"
              for line in copied_lines(text) if line not in spec_lines]
    return needs


def drift_needs(workspace: Path, key: str, index: Path, pins_text: str, needs: list[str], covered: bool) -> list[str]:
    """F4 and F5, when the workspace root is a git repository (the home repository): the spec pin names a home
    commit on the default branch, the spec has not changed since it, and the criteria copy matches it. `covered` is
    true when an UNAFFECTED line clears this part at the current spec."""
    if not own_repository(workspace):
        return []
    base = default_ref(workspace)
    if base is None:
        return ["the home repository's default branch cannot be found"]
    found, spec_rel = [], f"stories/{key}/spec.md"
    commit = parse_commits(pins_text).get("spec")
    if commit is None:
        if "spec" in parse_versions(pins_text):
            found.append("the spec pin names no home commit (spec v<n> @ <commit>)")
    elif git(workspace, "cat-file", "-e", f"{commit}^{{commit}}") is None:
        return found + [f"pinned home commit {commit[:7]} not found: run git fetch in the home repository"]
    elif git(workspace, "merge-base", "--is-ancestor", commit, base) is None:
        found.append(f"pinned home commit {commit[:7]} is not on the home repository's {base}")
    elif (not covered and not any(n.startswith("re-plan: spec") for n in needs)
          and git(workspace, "diff", "--quiet", commit, base, "--", spec_rel) is None):
        found.append(f"re-plan: {spec_rel} changed on {base} since {commit[:7]}")
    return found + criteria_needs(workspace, index, commit)


def story_current(workspace: Path, key: str)
````

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_story_status -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; `test_story_status` runs 45 tests; the suite is 564 tests, OK. Every existing assertion passes
unchanged: their workspace roots are plain folders, so `drift_needs` returns `[]`.

- [ ] **Step 5: Commit**

```bash
git add starter/workspace/scripts/story_status.py scripts/test_story_status.py
git commit -m "feat(starter): story status checks each part's home commit and its criteria copy (F4, F5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: `story_status.py`: the merge state from GitHub or git (F6)

**Files:**
- Modify: `starter/workspace/scripts/story_status.py`
- Test: `scripts/test_story_status.py` (add `import json` and `from unittest import mock`; new class `MergeStateTest`)

**Interfaces:**
- Consumes: `own_repository`, `default_ref`, `stage_rows`, `git` from Task 2 and the script.
- Produces:
  - `PartStatus.merge: str = "-"` (a new field with a default, after `needs`)
  - `run_gh(folder: Path, args: list[str]) -> str | None` (tests patch it)
  - `github_merge_state(folder: Path, key: str, number: int) -> tuple[str, str] | None`
  - `git_merge_state(folder: Path, index_rel: str) -> str | None`
  - `merge_state(folder: Path, key: str, number: int, index: Path, use_github: bool) -> tuple[str | None, str]`
  - `part_status(..., use_github: bool = True)`, `story_status(workspace, key, use_github: bool = True)`
  - the CLI flag `--no-github`; the status table's last column, `Merge state`.

- [ ] **Step 1: Write the failing tests**

In `scripts/test_story_status.py`, make the imports read:

```python
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock
from pathlib import Path
```

Then append above `if __name__ == "__main__":`:

```python
class MergeStateTest(unittest.TestCase):
    """F6: a part's merge state comes from GitHub when it can say, else from git; a hand-marked row that disagrees
    is reported."""

    PRS = [{"number": 4, "title": "[SHIP-1] part 1 of 2: add tracking endpoint", "state": "MERGED"},
           {"number": 7, "title": "[SHIP-1] part 1 of 2, plan v2: re-plan", "state": "MERGED"},
           {"number": 9, "title": "[SHIP-1] part 1 of 2, revision 2: rename the field", "state": "OPEN"},
           {"number": 10, "title": "[SHIP-1] part 1 of 2, revision 2: abandoned", "state": "CLOSED"},
           {"number": 12, "title": "[SHIP-12] part 1 of 1: another story", "state": "MERGED"}]

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        story(self.root)
        part(self.root, "web-portal")
        self.repo = self.root / "shipments-api"
        self.index = self.repo / "plans" / "SHIP-1" / "README.md"

    def commit_index(self, done, branch=None):
        if not (self.repo / ".git").exists():
            part(self.root, "shipments-api", done=done)
            run_git(self.repo, "init", "-q", "-b", "main")
        else:
            if branch:
                run_git(self.repo, "switch", "-q", "-c", branch)
            rows = "\n".join(f"| {s} | shipments-api | {'done' if s in done else 'to do'} |" for s in ALL)
            self.index.write_text(f"PINS       {PINS}\n\n| Stage | Runs in | Status |\n|---|---|---|\n{rows}\n",
                                  encoding="utf-8")
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "-m", "index")

    def status(self, use_github=True):
        return {r.repository: r for r in story_status.story_status(self.root, "SHIP-1", use_github)}["shipments-api"]

    def test_the_default_branchs_index_is_the_git_merge_state(self):
        self.commit_index(ALL)
        row = self.status()
        self.assertEqual((row.merge, row.needs), ("merged (git)", []))

    def test_a_merged_row_marked_on_a_branch_is_reported(self):
        self.commit_index(ALL[:4])
        self.commit_index(ALL, branch="feat/SHIP-1-1")
        row = self.status()
        self.assertEqual(row.merge, "not merged (git)")
        self.assertIn("the merged row is done, but git says not merged", row.needs)

    def test_a_checkout_behind_the_merge_is_reported(self):
        self.commit_index(ALL[:4])
        run_git(self.repo, "branch", "old")
        self.commit_index(ALL)
        run_git(self.repo, "switch", "-q", "old")
        self.assertIn("git says merged, but this checkout's merged row is not done (git pull the default branch)",
                      self.status().needs)

    def test_a_folder_with_no_committed_index_adds_nothing(self):
        part(self.root, "shipments-api", done=ALL)
        run_git(self.repo, "init", "-q", "-b", "main")
        run_git(self.repo, "commit", "-q", "--allow-empty", "-m", "x")
        row = self.status()
        self.assertEqual((row.merge, row.needs), ("-", []))

    def test_github_says_first_from_the_newest_code_pull_request(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://github.com/acme/shipments-api.git")
        calls = []

        def gh(folder, args):
            calls.append(args)
            return json.dumps(self.PRS)

        with mock.patch.object(story_status, "run_gh", gh):
            row = self.status()
        self.assertEqual(row.merge, "not merged (GitHub #9)")
        self.assertIn("the merged row is done, but GitHub #9 says not merged", row.needs)
        self.assertIn("SHIP-1 in:title", calls[0])

    def test_no_github_reads_only_git(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://github.com/acme/shipments-api.git")
        with mock.patch.object(story_status, "run_gh", side_effect=AssertionError("gh was called")):
            self.assertEqual(self.status(use_github=False).merge, "merged (git)")

    def test_a_remote_that_is_not_github_never_calls_gh(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://gitlab.example.com/acme/shipments-api.git")
        with mock.patch.object(story_status, "run_gh", side_effect=AssertionError("gh was called")):
            self.assertEqual(self.status().merge, "merged (git)")

    def test_the_status_file_has_the_merge_state_column(self):
        self.commit_index(ALL)
        with redirect_stdout(io.StringIO()):
            story_status.main(["SHIP-1", "--root", str(self.root), "--write", "--no-github"])
        status = (self.root / "stories" / "SHIP-1" / "status.md").read_text(encoding="utf-8")
        self.assertIn("| Part | Repository | Reached | Pins | Needs | Merge state |", status)
        self.assertIn("| merged (git) |", status)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_story_status.MergeStateTest -v`
Expected: ERROR or FAIL in all 8 (`story_status()` takes no `use_github`; `PartStatus` has no `merge`).

- [ ] **Step 3: Add the merge state**

Make these replacements in `starter/workspace/scripts/story_status.py`, in order:

1. Replace:

```python
    python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release]
```

with:

```python
    python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release] [--no-github]
```

2. Replace:

```python
whose SOURCE line names the commit it copies; every copied line must be in the spec at that commit."""
```

with:

```python
whose SOURCE line names the commit it copies; every copied line must be in the spec at that commit.

Each part's merge state comes from its newest code pull request on GitHub, when its repository has a GitHub remote and
gh answers (--no-github skips it), else from the default branch's copy of the part index, whose merged row reaches the
default branch only through the part's merge. A hand-marked merged row that disagrees is reported."""
```

3. Replace:

```python
import argparse
import re
import subprocess
```

with:

```python
import argparse
import json
import re
import shutil
import subprocess
```

4. Replace:

```python
SOURCE_LINE = re.compile(r"^SOURCE\s+(\S+)\s+(\S+)\s+@\s+([0-9a-fA-F]{7,40})\b", re.M)
```

with:

```python
SOURCE_LINE = re.compile(r"^SOURCE\s+(\S+)\s+(\S+)\s+@\s+([0-9a-fA-F]{7,40})\b", re.M)
GITHUB_REMOTE = re.compile(r"github\.com[:/]")
```

5. Replace:

```python
    needs: list[str] = field(default_factory=list)
```

with:

```python
    needs: list[str] = field(default_factory=list)
    merge: str = "-"        # the real merge state and its source, such as "merged (GitHub #12)"; "-" when unknown
```

6. Replace:

```python
                unaffected: dict[str, int]) -> PartStatus:
```

with:

```python
                unaffected: dict[str, int], use_github: bool = True) -> PartStatus:
```

7. Replace:

```python
    needs += drift_needs(workspace, key, index, pins_text, needs, covered)
    return PartStatus(number, repository, reached, pins_text or "-", needs)
```

with:

```python
    needs += drift_needs(workspace, key, index, pins_text, needs, covered)
    state, source = merge_state(workspace / repository, key, number, index, use_github)
    if state == "merged" and reached != "merged":
        needs.append(f"{source} says merged, but this checkout's merged row is not done (git pull the default branch)")
    elif state == "not merged" and reached == "merged":
        needs.append(f"the merged row is done, but {source} says not merged")
    return PartStatus(number, repository, reached, pins_text or "-", needs, f"{state} ({source})" if state else "-")
```

8. Replace:

```python
def story_current(workspace: Path, key: str)
```

with:

```python
def run_gh(folder: Path, args: list[str]) -> str | None:
    """gh's output, or None when gh is missing, fails, or takes longer than 30 seconds."""
    if shutil.which("gh") is None:
        return None
    try:
        result = subprocess.run(["gh", *args], cwd=folder, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def github_merge_state(folder: Path, key: str, number: int) -> tuple[str, str] | None:
    """('merged' or 'not merged', '#<n>') from the part's newest code pull request on GitHub; None when GitHub
    cannot say (no GitHub remote, no gh, no such pull request). The plan's own pull request ('..., plan v<n>: ...')
    and closed, unmerged ones are skipped; an open revision means the part is not merged at its latest version."""
    remote = git(folder, "remote", "get-url", "origin")
    if not remote or not GITHUB_REMOTE.search(remote):
        return None
    out = run_gh(folder, ["pr", "list", "--state", "all", "--search", f"{key} in:title", "--limit", "100",
                          "--json", "number,title,state"])
    try:
        prs = json.loads(out) if out else []
    except ValueError:
        return None
    title = re.compile(rf"^\[{re.escape(key)}\] part {number} of \d+(?:, revision \d+)?:")
    ours = sorted((p for p in prs if isinstance(p, dict) and title.match(str(p.get("title", "")))
                   and p.get("state") in ("OPEN", "MERGED")), key=lambda p: int(p.get("number", 0)))
    if not ours:
        return None
    return ("merged" if ours[-1]["state"] == "MERGED" else "not merged"), f"#{ours[-1]['number']}"


def git_merge_state(folder: Path, index_rel: str) -> str | None:
    """'merged' or 'not merged' from the default branch's copy of the part index, whose merged row reaches the
    default branch only through the part's merge (any merge method); None when the default branch has no copy."""
    base = default_ref(folder)
    text = git(folder, "show", f"{base}:{index_rel}") if base else None
    if text is None:
        return None
    return "merged" if stage_rows(text).get("merged") == "done" else "not merged"


def merge_state(folder: Path, key: str, number: int, index: Path, use_github: bool) -> tuple[str | None, str]:
    """F6: the part's real merge state and where it came from: GitHub when it can say, else git; (None, '-') when
    neither can (the folder is not its own repository, or its default branch has no part index yet)."""
    if not own_repository(folder):
        return None, "-"
    if use_github:
        found = github_merge_state(folder, key, number)
        if found:
            return found[0], f"GitHub {found[1]}"
    state = git_merge_state(folder, index.relative_to(folder).as_posix())
    return state, ("git" if state else "-")


def story_current(workspace: Path, key: str)
```

9. Replace:

```python
def story_status(workspace: Path, key: str) -> list[PartStatus]:
    current, unaffected, _ = story_current(workspace, key)
    plan = read(workspace / "stories" / key / "coordination-plan.md")
    return [part_status(workspace, key, n, repo, current, unaffected) for n, repo in parts(plan)]
```

with:

```python
def story_status(workspace: Path, key: str, use_github: bool = True) -> list[PartStatus]:
    current, unaffected, _ = story_current(workspace, key)
    plan = read(workspace / "stories" / key / "coordination-plan.md")
    return [part_status(workspace, key, n, repo, current, unaffected, use_github) for n, repo in parts(plan)]
```

10. Replace:

```python
             "| Part | Repository | Reached | Pins | Needs |", "|---|---|---|---|---|"]
    lines += [f"| {r.number} | {r.repository} | {r.reached} | {r.pins} | {'; '.join(r.needs) or '-'} |" for r in rows]
```

with:

```python
             "| Part | Repository | Reached | Pins | Needs | Merge state |", "|---|---|---|---|---|---|"]
    lines += [f"| {r.number} | {r.repository} | {r.reached} | {r.pins} | {'; '.join(r.needs) or '-'} | {r.merge} |"
              for r in rows]
```

11. Replace:

```python
    parser.add_argument("--check-release", action="store_true")
    args = parser.parse_args(argv)
```

with:

```python
    parser.add_argument("--check-release", action="store_true")
    parser.add_argument("--no-github", action="store_true")
    args = parser.parse_args(argv)
```

12. Replace:

```python
    rows = story_status(workspace, args.key)
```

with:

```python
    rows = story_status(workspace, args.key, use_github=not args.no_github)
```

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_story_status -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; 53 tests in `test_story_status`; the suite is 572, OK.
`test_write_saves_status_md_and_check_release_exits_1` still finds `| 1 | shipments-api | merged |` (the new column is
last), and `test_check_release_needs_each_repository_on_its_default_branch` still exits 0 then 1: its part indexes
are not committed, so the merge state is unknown and adds nothing.

- [ ] **Step 5: A live read-only run against GitHub (optional, when `gh` is signed in)**

Run: `cd /tmp && python3 -c "import sys; sys.path.insert(0, '/home/psharma/demos/aidlc/starter/workspace/scripts'); import story_status as s; print(s.run_gh(__import__('pathlib').Path('/home/psharma/demos/aidlc'), ['pr', 'list', '--state', 'all', '--limit', '3', '--json', 'number,title,state']))"`
Expected: a JSON list (or `None` when `gh` is absent or signed out). It confirms the `--json number,title,state`
fields exist in the installed `gh`. Record the output in the verification record (Task 12).

- [ ] **Step 6: Commit**

```bash
git add starter/workspace/scripts/story_status.py scripts/test_story_status.py
git commit -m "feat(starter): story status reads each part's merge state from GitHub or git and reports a row that disagrees (F6)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: The home repository's hygiene: `.gitignore`, CODEOWNERS, the runtime owner (F14)

**Files:**
- Modify: `starter/workspace/scripts/story_status.py` (`--write-gitignore`)
- Create: `starter/workspace/CODEOWNERS`
- Modify: `starter/workspace/.claude/settings.json` (two denies), `starter/workspace/WORKSPACE.md`,
  `skills/aidlc-onboard/assets/workspace.md`
- Test: `scripts/test_story_status.py` (new class `GitignoreTest`), `scripts/test_multirepo.py` (new class
  `HygieneTest`)

**Interfaces:**
- Produces: `GITIGNORE_BEGIN`, `GITIGNORE_END`, `REPOSITORY_NAME`;
  `workspace_repositories(text: str) -> list[str]`; `gitignore_text(existing: str, repositories: list[str]) -> str`;
  `write_gitignore(workspace: Path) -> tuple[int, str]`; the CLI `story_status.py --write-gitignore [--root DIR]`
  (the key becomes optional: `nargs="?"`).

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_story_status.py`, above `if __name__ == "__main__":`:

```python
WORKSPACE = ("# Workspace: shipments\n\n## Repositories\n| Repository | Owner | What it is | Rules file |\n"
             "|---|---|---|---|\n| shipments-api | core | the API | AGENTS.md |\n"
             "| `web/portal/` | web | the portal | AGENTS.md |\n| <repo> | <team> | <one line> | AGENTS.md |\n\n"
             "## How work runs here\n| not-a-repository | x |\n")


class GitignoreTest(unittest.TestCase):
    """F14: the home repository's .gitignore is generated from WORKSPACE.md's repository list."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = story_status.main([*argv, "--root", str(self.root)])
        return code, out.getvalue() + err.getvalue()

    def test_the_repositories_come_from_the_table(self):
        self.assertEqual(story_status.workspace_repositories(WORKSPACE), ["shipments-api", "web/portal"])

    def test_the_starter_lists_no_repository_yet(self):
        starter = Path(__file__).resolve().parents[1] / "starter" / "workspace" / "WORKSPACE.md"
        self.assertEqual(story_status.workspace_repositories(starter.read_text(encoding="utf-8")), [])

    def test_the_block_is_written_and_other_lines_are_kept(self):
        (self.root / "WORKSPACE.md").write_text(WORKSPACE, encoding="utf-8")
        (self.root / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        self.assertEqual(self.main("--write-gitignore")[0], 0)
        self.assertEqual((self.root / ".gitignore").read_text(encoding="utf-8"),
                         f"node_modules/\n\n{story_status.GITIGNORE_BEGIN}\n/shipments-api/\n/web/portal/\n"
                         f"{story_status.GITIGNORE_END}\n")

    def test_a_second_run_replaces_the_block(self):
        (self.root / "WORKSPACE.md").write_text(WORKSPACE, encoding="utf-8")
        self.main("--write-gitignore")
        (self.root / "WORKSPACE.md").write_text(WORKSPACE.replace("| shipments-api |", "| carrier-rates |"),
                                                encoding="utf-8")
        self.main("--write-gitignore")
        text = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/carrier-rates/\n", text)
        self.assertNotIn("/shipments-api/", text)
        self.assertEqual(text.count(story_status.GITIGNORE_BEGIN), 1)

    def test_no_workspace_guide_exits_2_and_an_empty_table_exits_1(self):
        self.assertEqual(self.main("--write-gitignore")[0], 2)
        (self.root / "WORKSPACE.md").write_text("# Workspace\n\n## Repositories\n| Repository |\n|---|\n",
                                                encoding="utf-8")
        self.assertEqual(self.main("--write-gitignore")[0], 1)
        self.assertFalse((self.root / ".gitignore").exists())

    def test_without_a_key_or_the_flag_it_exits_2(self):
        code, out = self.main()
        self.assertEqual(code, 2)
        self.assertIn("name the story's key", out)
```

Append to `scripts/test_multirepo.py`, above `if __name__ == "__main__":`:

```python
class HygieneTest(unittest.TestCase):
    """F14: the home repository's owners, its .gitignore and the runtime environment's owner."""

    def test_the_workspace_has_code_owners(self):
        owners = read("starter/workspace/CODEOWNERS")
        self.assertRegex(owners, r"(?m)^stories/\*\*\s+@your-org/your-team-leads$")
        self.assertRegex(owners, r"(?m)^compose\*\.yaml\s+@your-org/your-runtime-owner$")
        deny = json.loads(read("starter/workspace/.claude/settings.json"))["permissions"]["deny"]
        for rule in ("Edit(/CODEOWNERS)", "Edit(/.github/CODEOWNERS)"):
            self.assertIn(rule, deny)

    def test_the_workspace_guide_names_the_command_and_the_owner(self):
        for rel in ("starter/workspace/WORKSPACE.md", "skills/aidlc-onboard/assets/workspace.md"):
            text = flat(rel)
            self.assertIn("`python3 scripts/story_status.py --write-gitignore`", text, rel)
            self.assertIn("## Runtime environment", read(rel), rel)
            self.assertIn("Each fact has one owner, and only the owner changes it (ADR 0022)", text, rel)
            self.assertNotIn("never by copy", text, rel)
        self.assertEqual(VANISHING.findall(re.sub(r"`[^`\n]*`", "", read("skills/aidlc-onboard/assets/workspace.md"))), [])
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_story_status.GitignoreTest scripts.test_multirepo.HygieneTest -v`
Expected: FAIL or ERROR in all 8. `test_the_starter_lists_no_repository_yet` errors too (no
`workspace_repositories`).

- [ ] **Step 3: Add `--write-gitignore`**

Make these replacements in `starter/workspace/scripts/story_status.py`, in order:

1. Replace:

```python
    python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release] [--no-github]
```

with:

```python
    python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release] [--no-github]
    python3 scripts/story_status.py --write-gitignore [--root <workspace>]
```

2. Replace:

```python
default branch only through the part's merge. A hand-marked merged row that disagrees is reported."""
```

with:

```python
default branch only through the part's merge. A hand-marked merged row that disagrees is reported.

--write-gitignore writes the generated block of the root's .gitignore from the repository table in WORKSPACE.md, so
the home repository never tracks a child repository's files; every other line of .gitignore is kept."""
```

3. Replace:

```python
GITHUB_REMOTE = re.compile(r"github\.com[:/]")
```

with:

```python
GITHUB_REMOTE = re.compile(r"github\.com[:/]")
GITIGNORE_BEGIN = "# aidlc: the workspace's repositories, from WORKSPACE.md (story_status.py --write-gitignore; do not edit)"
GITIGNORE_END = "# aidlc: end of the repositories"
REPOSITORY_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._/-]*")
```

4. Replace:

```python
def main(argv: list[str]) -> int:
```

with:

```python
def workspace_repositories(text: str) -> list[str]:
    """The repositories WORKSPACE.md lists in its '## Repositories' table; the header, the separator and placeholder
    rows are skipped."""
    table = text.split("## Repositories", 1)[1].split("\n## ", 1)[0] if "## Repositories" in text else ""
    names = []
    for line in table.splitlines():
        if not line.strip().startswith("|"):
            continue
        name = line.strip().strip("|").split("|", 1)[0].strip().strip("`").strip().strip("/")
        if name.lower() != "repository" and REPOSITORY_NAME.fullmatch(name) and ".." not in name.split("/"):
            names.append(name)
    return list(dict.fromkeys(names))


def gitignore_text(existing: str, repositories: list[str]) -> str:
    """The workspace's .gitignore with its generated block replaced, or added at the end: one line per repository,
    so the home repository never tracks a child's files. Every line outside the block is kept as it is."""
    block = [GITIGNORE_BEGIN] + [f"/{name}/" for name in repositories] + [GITIGNORE_END]
    lines = existing.splitlines()
    if GITIGNORE_BEGIN in lines and GITIGNORE_END in lines[lines.index(GITIGNORE_BEGIN):]:
        start = lines.index(GITIGNORE_BEGIN)
        lines[start:lines.index(GITIGNORE_END, start) + 1] = block
    else:
        lines += ([""] if lines and lines[-1].strip() else []) + block
    return "\n".join(lines) + "\n"


def write_gitignore(workspace: Path) -> tuple[int, str]:
    """F14: (exit code, message) after writing the root's .gitignore from WORKSPACE.md's repository table."""
    guide = workspace / "WORKSPACE.md"
    if not guide.is_file():
        return 2, f"story_status: {guide.as_posix()} not found"
    repositories = workspace_repositories(read(guide))
    if not repositories:
        return 1, "story_status: WORKSPACE.md lists no repositories; .gitignore not written"
    target = workspace / ".gitignore"
    target.write_text(gitignore_text(read(target) if target.is_file() else "", repositories), encoding="utf-8")
    return 0, f"story_status: .gitignore lists the {len(repositories)} repositories in WORKSPACE.md"


def main(argv: list[str]) -> int:
```

5. Replace:

```python
    parser.add_argument("key")
```

with:

```python
    parser.add_argument("key", nargs="?")
```

6. Replace:

```python
    parser.add_argument("--no-github", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.root)
```

with:

```python
    parser.add_argument("--no-github", action="store_true")
    parser.add_argument("--write-gitignore", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.root)
    if args.write_gitignore:
        code, message = write_gitignore(workspace)
        print(message, file=sys.stderr if code else sys.stdout)
        if code or not args.key:
            return code
    if not args.key:
        print("story_status: name the story's key, or pass --write-gitignore", file=sys.stderr)
        return 2
```

- [ ] **Step 4: The workspace starter and its guide**

In `starter/workspace/WORKSPACE.md`, replace:

```markdown
  `python3 scripts/story_status.py <KEY> --check-release` (fails unless every part is merged at the current versions).
```

with:

```markdown
  `python3 scripts/story_status.py <KEY> --check-release` (fails unless every part is merged at the current versions).
- After the repository table above changes: `python3 scripts/story_status.py --write-gitignore` (the root's
  `.gitignore` then lists every repository, so this home repository never tracks their files).
```

In `starter/workspace/WORKSPACE.md`, replace:

```markdown
- Contracts by version, never by copy: read another repository's contract at its release tag.
```

with:

```markdown
- Contracts by version: read another repository's contract at its published tag (`api-v<version>`). A consumer's
  copy under `contracts/<provider>/` is read-only; its `SOURCE` names the tag, the commit and the hash (ADR 0022).
- Each fact has one owner, and only the owner changes it (ADR 0022): the story's shared documents live here, in
  `stories/<KEY>/`; each part's plan, bundles, criteria copy, evidence and review live in its repository.
```

In `starter/workspace/WORKSPACE.md`, replace:

```markdown
## Tools
```

with:

```markdown
## Runtime environment
- Owner: <team>. The compose files and feature flags the repositories run with together belong to this owner; a
  change to them is that owner's pull request.

## Tools
```

In `skills/aidlc-onboard/assets/workspace.md`, replace:

```markdown
  `python3 scripts/story_status.py <KEY> --check-release` (fails unless every part is merged at the current versions).
```

with:

```markdown
  `python3 scripts/story_status.py <KEY> --check-release` (fails unless every part is merged at the current versions).
- After the repository table above changes: `python3 scripts/story_status.py --write-gitignore` (the root's
  `.gitignore` then lists every repository, so this home repository never tracks their files).
```

In `skills/aidlc-onboard/assets/workspace.md`, replace:

```markdown
- Contracts by version, never by copy: read another repository's contract at its release tag.
```

with:

```markdown
- Contracts by version: read another repository's contract at its published tag (`api-v<version>`). A consumer's
  copy under `contracts/<provider>/` is read-only; its `SOURCE` names the tag, the commit and the hash (ADR 0022).
- Each fact has one owner, and only the owner changes it (ADR 0022): the story's shared documents live here, in
  `stories/<KEY>/`; each part's plan, bundles, criteria copy, evidence and review live in its repository.
```

In `skills/aidlc-onboard/assets/workspace.md`, replace:

```markdown
## Tools
```

with:

```markdown
## Runtime environment
- Owner: {{team}}. The compose files and feature flags the repositories run with together belong to this owner; a
  change to them is that owner's pull request.

## Tools
```

Create `starter/workspace/CODEOWNERS`:

```text
# The home repository (the workspace root): every change needs a review from its owners. Put this file at
# .github/CODEOWNERS and replace the teams (aidlc ADR 0022).
*                    @your-org/your-team-leads
# The story documents: the spec, the design, the coordination plan, the release records.
stories/**           @your-org/your-team-leads
WORKSPACE.md         @your-org/your-team-leads
CLAUDE.md            @your-org/your-team-leads
# Scripts and settings that enforce the rules.
scripts/             @your-org/your-team-leads
.claude/             @your-org/your-team-leads
.github/             @your-org/your-team-leads
# The runtime environment the repositories run with together: its named owner (WORKSPACE.md).
compose*.yaml        @your-org/your-runtime-owner
compose*.yml         @your-org/your-runtime-owner
flags/               @your-org/your-runtime-owner
```

In `starter/workspace/.claude/settings.json`, replace:

```json
      "Edit(/scripts/story_status.py)",
```

with:

```json
      "Edit(/scripts/story_status.py)",
      "Edit(/CODEOWNERS)",
      "Edit(/.github/CODEOWNERS)",
```

- [ ] **Step 5: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_story_status scripts.test_multirepo -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; the suite is 580, OK. `check_starters` still passes (the workspace keeps every secret deny);
`test_the_workspace_keeps_nothing_for_a_one_repository_story` still passes (no "pointer" in the guide);
`test_the_workspace_root_may_write_incidents_and_feedback` still finds its sentence.

- [ ] **Step 6: Commit**

```bash
git add starter/workspace/scripts/story_status.py starter/workspace/CODEOWNERS starter/workspace/.claude/settings.json starter/workspace/WORKSPACE.md skills/aidlc-onboard/assets/workspace.md scripts/test_story_status.py scripts/test_multirepo.py
git commit -m "feat(starter): the home repository's gitignore comes from WORKSPACE.md; leads own stories; a named runtime owner (F14)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: `check_contract_version.py`: the provider's contract check (F9, D9)

**Files:**
- Create: `starter/repo/scripts/check_contract_version.py`
- Create: `scripts/test_check_contract.py`

**Interfaces:**
- Produces (Task 6 imports the first three; Task 7's workflows run the CLI):
  - `TAG` (`^api-v(\d+\.\d+\.\d+)$`), `SEMVER`
  - `info_version(text: str) -> str | None`
  - `semver(value: str | None) -> tuple[int, int, int] | None`
  - `show(version) -> str`, `git(root, *args) -> str | None`
  - `published(root: Path) -> list[tuple[tuple[int, int, int], str]]`
  - `run_oasdiff(oasdiff: str, base: str, revision: str, suffix: str) -> tuple[int, str]`
  - `check(root: Path, contract: str, oasdiff: str = "oasdiff") -> tuple[list[str], list[str]]` (problems, notes)
  - `publish_tag(root: Path, contract: str) -> tuple[str | None, list[str]]`
  - `main(argv: list[str] | None = None) -> int`: `--contract PATH [--oasdiff PATH] [--publish-tag] [--root DIR]`
  - In the tests: `Provider(tmp)` with `.root`, `.oasdiff` (a fake), `.commit(text) -> str`, `.check()`;
    `contract(version, paths) -> str`; `git(root, *args) -> str`.

- [ ] **Step 1: Write the failing tests**

The fake oasdiff in this file reports a breaking change when a path of the base is gone, and records its arguments
beside itself. Create `scripts/test_check_contract.py`:

```python
"""Tests for starter/repo/scripts/check_contract_version.py (the provider) and check_contract_pin.py (the consumer).
A fake oasdiff stands in for the real one: it reports a breaking change when a path of the base is gone."""
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import check_contract_version  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null", "-c", "tag.gpgsign=false"]
FAKE_OASDIFF = """#!{python}
import pathlib, sys
pathlib.Path(sys.argv[0] + ".args").write_text("\\n".join(sys.argv[1:]))
base, revision = (pathlib.Path(p).read_text().splitlines() for p in sys.argv[-2:])
gone = [line for line in base if line.startswith("  /") and line not in revision]
if gone:
    print("error [api-path-removed-without-deprecation] " + gone[0].strip())
    sys.exit(1)
"""


def contract(version: str = "1.0.0", paths: tuple[str, ...] = ("/shipments/{id}",)) -> str:
    body = "".join(f"  {p}:\n    get:\n      responses:\n        '200':\n          description: ok\n" for p in paths)
    return f"openapi: 3.0.3\ninfo:\n  title: Shipments\n  version: {version}\n  contact:\n    name: core\npaths:\n{body}"


def git(root: Path, *args: str) -> str:
    return subprocess.run(GIT + ["-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


class Provider:
    """A provider repository whose main published api-v1.0.0."""

    def __init__(self, tmp: Path):
        self.root = tmp / "shipments-api"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", "main")
        self.commit(contract("1.0.0"))
        git(self.root, "tag", "api-v1.0.0")
        self.oasdiff = tmp / "oasdiff"
        self.oasdiff.write_text(FAKE_OASDIFF.format(python=sys.executable), encoding="utf-8")
        self.oasdiff.chmod(0o755)

    def commit(self, text: str) -> str:
        (self.root / "openapi.yaml").write_text(text, encoding="utf-8")
        git(self.root, "add", "openapi.yaml")
        git(self.root, "commit", "-q", "-m", "contract")
        return git(self.root, "rev-parse", "HEAD")

    def check(self) -> tuple[list[str], list[str]]:
        return check_contract_version.check(self.root, "openapi.yaml", str(self.oasdiff))


class InfoVersionTest(unittest.TestCase):
    def test_yaml_json_and_quotes(self):
        v = check_contract_version.info_version
        self.assertEqual(v(contract("2.1.0")), "2.1.0")
        self.assertEqual(v("openapi: 3.1.0\ninfo:\n  title: x\n  version: '3.0.1'  # pinned\n"), "3.0.1")
        self.assertEqual(v('{"openapi": "3.1.0", "info": {"title": "x", "version": "1.2.3"}}'), "1.2.3")

    def test_a_nested_version_is_not_info_version(self):
        text = "info:\n  title: x\n  contact:\n    version: 9.9.9\npaths: {}\nversion: 8.8.8\n"
        self.assertIsNone(check_contract_version.info_version(text))


class ProviderTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.provider = Provider(Path(tmp.name))

    def test_the_first_version_needs_no_tag(self):
        git(self.provider.root, "tag", "-d", "api-v1.0.0")
        problems, notes = self.provider.check()
        self.assertEqual(problems, [])
        self.assertIn("becomes the first published version", notes[0])

    def test_an_unchanged_contract_is_clean(self):
        self.assertEqual(self.provider.check(), ([], ["openapi.yaml is unchanged since api-v1.0.0"]))

    def test_an_additive_change_with_a_new_minor_is_clean(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.1.0", ("/shipments/{id}", "/shipments")),
                                                         encoding="utf-8")
        problems, notes = self.provider.check()
        self.assertEqual(problems, [])
        self.assertEqual(notes, ["no breaking change since api-v1.0.0"])
        args = Path(str(self.provider.oasdiff) + ".args").read_text().splitlines()
        self.assertEqual(args[:4], ["breaking", "--fail-on", "ERR", "--allow-external-refs=false"])

    def test_a_change_without_a_new_version_is_a_problem(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.0.0", ("/shipments/{id}", "/shipments")),
                                                         encoding="utf-8")
        self.assertEqual(self.provider.check()[0], ["openapi.yaml changed since api-v1.0.0, but info.version 1.0.0 "
                                                    "is not above 1.0.0: raise it"])

    def test_a_breaking_change_needs_a_new_major(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.1.0", ("/parcels/{id}",)), encoding="utf-8")
        self.assertEqual(self.provider.check()[0], ["a breaking change since api-v1.0.0 without a new MAJOR version: "
                                                    "make it additive, or raise MAJOR with the consumers' agreement "
                                                    "(expand and contract)"])

    def test_a_breaking_change_with_a_new_major_asks_for_the_agreement(self):
        (self.provider.root / "openapi.yaml").write_text(contract("2.0.0", ("/parcels/{id}",)), encoding="utf-8")
        problems, notes = self.provider.check()
        self.assertEqual(problems, [])
        self.assertIn("records each consumer's agreement", notes[0])
        self.assertIn("api-path-removed", notes[1])

    def test_a_missing_oasdiff_fails_closed(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.1.0", ("/shipments",)), encoding="utf-8")
        problems, _ = check_contract_version.check(self.provider.root, "openapi.yaml",
                                                   str(self.provider.root / "no-such-oasdiff"))
        self.assertEqual(problems, ["oasdiff could not compare the contracts (exit 127)"])

    def test_a_bad_version_is_a_problem(self):
        (self.provider.root / "openapi.yaml").write_text(contract("v2"), encoding="utf-8")
        self.assertEqual(self.provider.check()[0], ["openapi.yaml: info.version must be MAJOR.MINOR.PATCH, not 'v2'"])

    def test_publish_names_a_new_version_only(self):
        publish = check_contract_version.publish_tag
        self.assertEqual(publish(self.provider.root, "openapi.yaml"), (None, []))
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        self.assertEqual(publish(self.provider.root, "openapi.yaml"), ("api-v1.1.0", []))

    def test_publish_refuses_a_lower_or_a_changed_published_version(self):
        publish = check_contract_version.publish_tag
        git(self.provider.root, "tag", "api-v1.2.0")
        self.provider.commit(contract("1.1.0"))
        self.assertEqual(publish(self.provider.root, "openapi.yaml")[1],
                         ["openapi.yaml 1.1.0 is not above the published api-v1.2.0"])
        self.provider.commit(contract("1.0.0", ("/other",)))
        self.assertIn("a published version never changes", publish(self.provider.root, "openapi.yaml")[1][0])

    def test_the_command_prints_only_the_tag(self):
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check_contract_version.main(["--contract", "openapi.yaml", "--publish-tag",
                                                "--root", str(self.provider.root)])
        self.assertEqual((code, out.getvalue()), (0, "api-v1.1.0\n"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_check_contract -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'check_contract_version'`.

- [ ] **Step 3: Write the script**

Create `starter/repo/scripts/check_contract_version.py`:

```python
#!/usr/bin/env python3
"""The provider's contract check (aidlc ADR 0022; change list F9, decision D9). The provider owns the OpenAPI file
that its AGENTS.md names, and publishes each version as the git tag api-v<info.version>, only from the default
branch.

    python3 scripts/check_contract_version.py --contract openapi.yaml [--oasdiff PATH] [--root DIR]
    python3 scripts/check_contract_version.py --contract openapi.yaml --publish-tag [--root DIR]

On a pull request it compares the contract with the last published version (the highest api-v* tag in the clone):
a changed contract must raise info.version, and a breaking change (oasdiff breaking --fail-on ERR) must raise its
MAJOR, with the consumers' agreement recorded in the pull request, which a person checks. oasdiff runs with external
$refs refused, because a pull request is untrusted. --publish-tag prints the tag to create for the contract on this
commit, or nothing when that version is already published. Exit 0 clean, 1 problems. Standard library only; oasdiff
is a release binary that the workflow downloads at a pinned version and checks against its sha256."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TAG = re.compile(r"^api-v(\d+\.\d+\.\d+)$")
Semver = tuple[int, int, int]


def info_version(text: str) -> str | None:
    """info.version of an OpenAPI document in JSON, or in YAML written in block style; None when it has none."""
    if text.lstrip().startswith("{"):
        try:
            value = json.loads(text).get("info", {}).get("version")
        except (ValueError, AttributeError):
            return None
        return None if value is None else str(value)
    inside, indent = False, None
    for line in text.splitlines():
        if re.match(r"^info:\s*(#.*)?$", line):
            inside = True
            continue
        if not inside or not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[:1].isspace():
            break
        depth = len(line) - len(line.lstrip())
        indent = depth if indent is None else indent
        m = re.match(r"^\s+version:\s*(['\"]?)([^'\"#\s]+)\1\s*(#.*)?$", line)
        if m and depth == indent:
            return m.group(2)
    return None


def semver(value: str | None) -> Semver | None:
    m = SEMVER.match(value or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def show(version: Semver) -> str:
    return ".".join(map(str, version))


def git(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def published(root: Path) -> list[tuple[Semver, str]]:
    """Every api-v<MAJOR.MINOR.PATCH> tag in the clone, lowest version first."""
    found = []
    for tag in (git(root, "tag", "--list", "api-v*") or "").split():
        m = TAG.match(tag)
        if m:
            found.append((semver(m.group(1)), tag))
    return sorted(found)


def run_oasdiff(oasdiff: str, base: str, revision: str, suffix: str) -> tuple[int, str]:
    """oasdiff's exit code and output for `breaking --fail-on ERR` between two contract texts: 0 no breaking change,
    1 a breaking change, anything else a failure to compare. External $refs are refused."""
    with tempfile.TemporaryDirectory() as tmp:
        old, new = Path(tmp) / f"base{suffix}", Path(tmp) / f"revision{suffix}"
        old.write_text(base, encoding="utf-8")
        new.write_text(revision, encoding="utf-8")
        try:
            result = subprocess.run([oasdiff, "breaking", "--fail-on", "ERR", "--allow-external-refs=false",
                                     str(old), str(new)], capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as error:
            return 127, f"cannot run {oasdiff}: {error}"
    return result.returncode, (result.stdout + result.stderr).strip()


def check(root: Path, contract: str, oasdiff: str = "oasdiff") -> tuple[list[str], list[str]]:
    """(problems, notes) for the contract in the working tree against its last published version."""
    path = root / contract
    if not path.is_file():
        return [], [f"no contract at {contract}; nothing to check"]
    head = path.read_text(encoding="utf-8")
    version = semver(info_version(head))
    if version is None:
        return [f"{contract}: info.version must be MAJOR.MINOR.PATCH, not {info_version(head)!r}"], []
    tags = published(root)
    if not tags:
        return [], [f"no api-v* tag yet: {contract} {show(version)} becomes the first published version"]
    last, tag = tags[-1]
    base = git(root, "show", f"{tag}:{contract}")
    if base is None:
        return [f"{tag} has no {contract}: when the contract moves, name its new path in AGENTS.md and in each "
                f"consumer's SOURCE"], []
    if base == head:
        return [], [f"{contract} is unchanged since {tag}"]
    problems, notes = [], []
    if version <= last:
        problems.append(f"{contract} changed since {tag}, but info.version {show(version)} is not above "
                        f"{show(last)}: raise it")
    code, output = run_oasdiff(oasdiff, base, head, path.suffix)
    if code == 0:
        notes.append(f"no breaking change since {tag}")
    elif code == 1 and version[0] > last[0]:
        notes.append(f"a breaking change since {tag}, with MAJOR raised to {version[0]}: the pull request records "
                     f"each consumer's agreement (a person checks it)")
    elif code == 1:
        problems.append(f"a breaking change since {tag} without a new MAJOR version: make it additive, or raise "
                        f"MAJOR with the consumers' agreement (expand and contract)")
    else:
        problems.append(f"oasdiff could not compare the contracts (exit {code})")
    if output:
        notes.append(output[:4000])
    return problems, notes


def publish_tag(root: Path, contract: str) -> tuple[str | None, list[str]]:
    """(the tag to create on this commit, problems): no tag when there is no contract or its version is published."""
    path = root / contract
    if not path.is_file():
        return None, []
    head = path.read_text(encoding="utf-8")
    version = semver(info_version(head))
    if version is None:
        return None, [f"{contract}: info.version must be MAJOR.MINOR.PATCH, not {info_version(head)!r}"]
    tag, tags = f"api-v{show(version)}", published(root)
    if any(name == tag for _, name in tags):
        if git(root, "show", f"{tag}:{contract}") != head:
            return None, [f"{contract} differs from the published {tag} without a new info.version: a published "
                          f"version never changes"]
        return None, []
    if tags and version <= tags[-1][0]:
        return None, [f"{contract} {show(version)} is not above the published {tags[-1][1]}"]
    return tag, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", required=True)
    parser.add_argument("--oasdiff", default="oasdiff")
    parser.add_argument("--publish-tag", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.publish_tag:
        tag, problems = publish_tag(root, args.contract)
        for problem in problems:
            print(problem, file=sys.stderr)
        if tag:
            print(tag)
        return 1 if problems else 0
    problems, notes = check(root, args.contract, args.oasdiff)
    for note in notes:
        print(note)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"check_contract_version: {args.contract}: versioned and compatible with its last published tag")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_check_contract -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS (13 tests); the suite is 593, OK.

- [ ] **Step 5: Commit**

```bash
git add starter/repo/scripts/check_contract_version.py scripts/test_check_contract.py
git commit -m "feat(starter): the provider's contract check: a change raises the version, a breaking change raises MAJOR (F9, D9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: `check_contract_pin.py`: the consumer's vendored copy (F9)

**Files:**
- Create: `starter/repo/scripts/check_contract_pin.py`
- Test: `scripts/test_check_contract.py` (import `check_contract_pin`; new class `ConsumerTest`)

**Interfaces:**
- Consumes: `TAG`, `info_version`, `semver` from `check_contract_version.py` (same folder).
- Produces:
  - `KEYS = ("repository", "tag", "commit", "path", "sha256")`
  - `read_source(text: str) -> dict[str, str]`, `source_text(fields: dict[str, str]) -> str`
  - `sha256(data: bytes) -> str`, `copy_of(folder: Path, path: str) -> Path`
  - `offline_problems(folder: Path) -> list[str]`, `online_problems(folder: Path) -> list[str]`
  - `fetch(repository: str, tag: str, path: str) -> tuple[str, bytes] | str`
  - `update(root, provider, tag, repository=None, path=None) -> tuple[int, list[str]]`
  - `main(argv) -> int`: `[--online] [--update PROVIDER TAG [--repository URL --path PATH]] [--root DIR]`
  - The `SOURCE` file: five `key: value` lines (`repository`, `tag`, `commit`, `path`, `sha256`).

- [ ] **Step 1: Write the failing tests**

In `scripts/test_check_contract.py`, change the import line `import check_contract_version  # noqa: E402` to:

```python
import check_contract_pin  # noqa: E402
import check_contract_version  # noqa: E402
```

Append above `if __name__ == "__main__":`:

```python
class ConsumerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.provider = Provider(Path(tmp.name))
        self.root = Path(tmp.name) / "web-portal"
        self.root.mkdir()
        self.folder = self.root / "contracts" / "shipments-api"

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check_contract_pin.main([*argv, "--root", str(self.root)])
        return code, out.getvalue() + err.getvalue()

    def vendor(self, tag="api-v1.0.0"):
        return self.main("--update", "shipments-api", tag, "--repository", str(self.provider.root),
                         "--path", "openapi.yaml")

    def test_no_contracts_is_clean(self):
        self.assertEqual(self.main(), (0, "check_contract_pin: no vendored contracts\n"))

    def test_update_writes_the_copy_and_its_source(self):
        code, out = self.vendor()
        self.assertEqual(code, 0, out)
        source = check_contract_pin.read_source((self.folder / "SOURCE").read_text(encoding="utf-8"))
        self.assertEqual(source["tag"], "api-v1.0.0")
        self.assertEqual(source["commit"], git(self.provider.root, "rev-parse", "api-v1.0.0^{commit}"))
        self.assertEqual((self.folder / "openapi.yaml").read_text(encoding="utf-8"), contract("1.0.0"))
        self.assertEqual(self.main()[0], 0)
        self.assertEqual(self.main("--online")[0], 0)

    def test_an_edited_copy_is_a_problem(self):
        self.vendor()
        (self.folder / "openapi.yaml").write_text(contract("1.0.0", ("/shipments",)), encoding="utf-8")
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn("contracts/shipments-api/openapi.yaml: differs from the copy SOURCE names (sha256)", out)

    def test_a_source_missing_a_field_is_a_problem(self):
        self.vendor()
        text = (self.folder / "SOURCE").read_text(encoding="utf-8")
        (self.folder / "SOURCE").write_text("\n".join(line for line in text.splitlines() if not line.startswith("commit:")),
                                            encoding="utf-8")
        self.assertIn("contracts/shipments-api/SOURCE: commit missing", self.main()[1])

    def test_a_copy_whose_version_is_not_the_tags_is_a_problem(self):
        self.vendor()
        text = contract("1.1.0")
        (self.folder / "openapi.yaml").write_text(text, encoding="utf-8")
        source = (self.folder / "SOURCE").read_text(encoding="utf-8")
        old = check_contract_pin.read_source(source)["sha256"]
        (self.folder / "SOURCE").write_text(source.replace(old, check_contract_pin.sha256(text.encode())),
                                            encoding="utf-8")
        self.assertIn("info.version is '1.1.0', but SOURCE pins api-v1.0.0", self.main()[1])

    def test_a_moved_tag_is_found_online(self):
        self.vendor()
        self.provider.commit(contract("1.0.0", ("/moved",)))
        git(self.provider.root, "tag", "-f", "api-v1.0.0")
        code, out = self.main("--online")
        self.assertEqual(code, 1)
        self.assertIn("a published version moved; ask the provider", out)

    def test_update_moves_the_pin_to_a_named_version(self):
        self.vendor()
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        git(self.provider.root, "tag", "api-v1.1.0")
        self.assertEqual(self.main("--update", "shipments-api", "api-v1.1.0")[0], 0)
        self.assertEqual(check_contract_pin.read_source((self.folder / "SOURCE").read_text(encoding="utf-8"))["tag"],
                         "api-v1.1.0")
        self.assertEqual(self.main("--online")[0], 0)

    def test_update_never_follows_latest(self):
        code, out = self.main("--update", "shipments-api", "latest", "--repository", str(self.provider.root),
                              "--path", "openapi.yaml")
        self.assertEqual(code, 2)
        self.assertIn("never latest", out)

    def test_an_unpublished_tag_cannot_be_fetched(self):
        code, out = self.vendor("api-v9.0.0")
        self.assertEqual(code, 1)
        self.assertIn("cannot fetch api-v9.0.0", out)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_check_contract -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'check_contract_pin'`.

- [ ] **Step 3: Write the script**

Create `starter/repo/scripts/check_contract_pin.py`:

```python
#!/usr/bin/env python3
"""The consumer's contract pin (aidlc ADR 0022; change list F9). A consumer keeps a read-only copy of each provider's
published contract in contracts/<provider>/, beside a SOURCE file that names where the copy came from:

    repository: <git URL of the provider repository>
    tag:        api-v<MAJOR.MINOR.PATCH>
    commit:     <the full commit the tag named when the copy was taken>
    path:       <the contract's path in the provider repository>
    sha256:     <the copy's sha256>

    python3 scripts/check_contract_pin.py [--root DIR]            every copy matches its SOURCE (offline; CI runs it)
    python3 scripts/check_contract_pin.py --online [--root DIR]   also: the tag still names that commit, and the
                                                                  file there hashes the same
    python3 scripts/check_contract_pin.py --update <provider> <tag> [--repository URL --path PATH] [--root DIR]

--update fetches one published version, named exactly (never "latest"), and rewrites the copy and SOURCE; commit
both in a slice whose MAY CHANGE names contracts/<provider>/**, in a reviewed pull request. --repository and --path
are needed the first time only. Exit 0 clean, 1 problems, 2 a usage error. Standard library only; git fetches, with
the credentials it already has."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_contract_version import TAG, info_version, semver  # noqa: E402

KEYS = ("repository", "tag", "commit", "path", "sha256")
PROVIDER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def read_source(text: str) -> dict[str, str]:
    found = {}
    for line in text.splitlines():
        m = re.match(r"^([a-z0-9]+):\s*(\S.*?)\s*$", line)
        if m:
            found[m.group(1)] = m.group(2)
    return found


def source_text(fields: dict[str, str]) -> str:
    return "".join(f"{key + ':':<12}{fields[key]}\n" for key in KEYS)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def copy_of(folder: Path, path: str) -> Path:
    return folder / PurePosixPath(path).name


def offline_problems(folder: Path) -> list[str]:
    """The copy in contracts/<provider>/ is exactly the published version its SOURCE names."""
    rel = f"contracts/{folder.name}"
    if not (folder / "SOURCE").is_file():
        return [f"{rel}: no SOURCE naming the repository, tag, commit, path and sha256 of the copy"]
    fields = read_source((folder / "SOURCE").read_text(encoding="utf-8"))
    missing = [key for key in KEYS if key not in fields]
    if missing:
        return [f"{rel}/SOURCE: {', '.join(missing)} missing"]
    problems = []
    tag = TAG.match(fields["tag"])
    if not tag:
        problems.append(f"{rel}/SOURCE: {fields['tag']} is not a published version (api-v<MAJOR.MINOR.PATCH>)")
    if not re.fullmatch(r"[0-9a-f]{40}", fields["commit"]):
        problems.append(f"{rel}/SOURCE: commit must be the full 40-character commit")
    copy = copy_of(folder, fields["path"])
    if not copy.is_file():
        return problems + [f"{rel}: no {copy.name} beside SOURCE"]
    data = copy.read_bytes()
    if sha256(data) != fields["sha256"].lower():
        problems.append(f"{rel}/{copy.name}: differs from the copy SOURCE names (sha256); the copy is read-only: "
                        f"change it with --update, in its own pull request")
    elif tag and info_version(data.decode("utf-8", errors="replace")) != tag.group(1):
        problems.append(f"{rel}/{copy.name}: info.version is {info_version(data.decode('utf-8', errors='replace'))!r}, "
                        f"but SOURCE pins {fields['tag']}")
    return problems


def fetch(repository: str, tag: str, path: str) -> tuple[str, bytes] | str:
    """(the commit the tag names, the contract's bytes there), or why they cannot be read."""
    with tempfile.TemporaryDirectory() as tmp:
        def run(*args: str, text: bool = True) -> subprocess.CompletedProcess:
            return subprocess.run(["git", "-C", tmp, *args], capture_output=True, text=text, timeout=120)
        try:
            run("init", "-q")
            got = run("fetch", "-q", "--depth", "1", "--no-tags", repository, f"refs/tags/{tag}:refs/tags/{tag}")
            if got.returncode != 0:
                return f"cannot fetch {tag} from {repository}: {got.stderr.strip()[:200]}"
            commit = run("rev-parse", f"refs/tags/{tag}^{{commit}}").stdout.strip()
            blob = run("show", f"refs/tags/{tag}:{path}", text=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            return f"cannot fetch {tag} from {repository}: {error}"
        if blob.returncode != 0:
            return f"{tag} in {repository} has no {path}"
        return commit, blob.stdout


def online_problems(folder: Path) -> list[str]:
    """The tag still names the commit SOURCE recorded, and the file there is the copy: a published version never
    changes."""
    fields = read_source((folder / "SOURCE").read_text(encoding="utf-8"))
    got = fetch(fields["repository"], fields["tag"], fields["path"])
    if isinstance(got, str):
        return [f"contracts/{folder.name}: {got}"]
    commit, data = got
    if commit != fields["commit"]:
        return [f"contracts/{folder.name}: {fields['tag']} now names {commit[:12]}, not {fields['commit'][:12]}: "
                f"a published version moved; ask the provider"]
    if sha256(data) != fields["sha256"].lower():
        return [f"contracts/{folder.name}: {fields['path']} at {fields['tag']} does not hash to SOURCE's sha256"]
    return []


def update(root: Path, provider: str, tag: str, repository: str | None = None,
           path: str | None = None) -> tuple[int, list[str]]:
    """Fetches one published version and rewrites contracts/<provider>/ and its SOURCE."""
    if not PROVIDER.fullmatch(provider):
        return 2, [f"{provider}: a provider is named by one folder name under contracts/"]
    if not TAG.match(tag):
        return 2, [f"{tag}: name one published version, api-v<MAJOR.MINOR.PATCH>; never latest"]
    folder = root / "contracts" / provider
    old = read_source((folder / "SOURCE").read_text(encoding="utf-8")) if (folder / "SOURCE").is_file() else {}
    repository, path = repository or old.get("repository"), path or old.get("path")
    if not repository or not path:
        return 2, [f"contracts/{provider} has no SOURCE yet: pass --repository and --path"]
    got = fetch(repository, tag, path)
    if isinstance(got, str):
        return 1, [got]
    commit, data = got
    folder.mkdir(parents=True, exist_ok=True)
    if old.get("path") and copy_of(folder, old["path"]).name != copy_of(folder, path).name:
        copy_of(folder, old["path"]).unlink(missing_ok=True)
    copy_of(folder, path).write_bytes(data)
    fields = {"repository": repository, "tag": tag, "commit": commit, "path": path, "sha256": sha256(data)}
    (folder / "SOURCE").write_text(source_text(fields), encoding="utf-8")
    messages = [f"contracts/{provider}: now {tag} ({commit[:12]}); commit the copy and SOURCE together, in a slice "
                f"whose MAY CHANGE names contracts/{provider}/**"]
    before = TAG.match(old.get("tag", ""))
    if before and semver(before.group(1)) > semver(TAG.match(tag).group(1)):
        messages.append(f"note: {tag} is older than the {old['tag']} it replaces")
    return 0, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--update", nargs=2, metavar=("PROVIDER", "TAG"))
    parser.add_argument("--repository")
    parser.add_argument("--path")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.update:
        code, messages = update(root, *args.update, repository=args.repository, path=args.path)
        for message in messages:
            print(message, file=sys.stderr if code else sys.stdout)
        return code
    contracts = root / "contracts"
    folders = sorted(p for p in contracts.iterdir() if p.is_dir()) if contracts.is_dir() else []
    if not folders:
        print("check_contract_pin: no vendored contracts")
        return 0
    problems = []
    for folder in folders:
        found = offline_problems(folder)
        problems += found if found or not args.online else online_problems(folder)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"check_contract_pin: {len(folders)} vendored contract(s) match their SOURCE"
              + (" and their published tags" if args.online else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_check_contract -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS (22 tests); the suite is 602, OK. The fetch tests use a local provider repository as the URL, so
they need no network.

- [ ] **Step 5: Commit**

```bash
git add starter/repo/scripts/check_contract_pin.py scripts/test_check_contract.py
git commit -m "feat(starter): the consumer pins each contract as a read-only copy with its SOURCE, checked offline (F9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 7: The contract workflows, the CI job and the guide (F9)

**Files:**
- Create: `starter/repo/.github/workflows/contract-check.yml`, `starter/repo/.github/workflows/contract-publish.yml`
- Modify: `starter/repo/.github/workflows/ci.yml` (new job `contract-pin`, appended)
- Modify: `starter/repo/AGENTS.md`, `skills/aidlc-onboard/assets/agents-md.md` (Commands; Where to look)
- Test: `scripts/test_check_slice.py` (new class `ContractPinScopeTest`), `scripts/test_multirepo.py` (new class
  `ContractWorkflowTest`)

**Interfaces:**
- Consumes: the CLIs of Tasks 5 and 6; `Repo` and `bundle()` from `scripts/test_check_slice.py`.

- [ ] **Step 1: Verify oasdiff's release, checksum and flags (read-only)**

```bash
gh api repos/oasdiff/oasdiff/releases/tags/v1.35.0 --jq '.published_at, (.assets[] | select(.name == "oasdiff_1.35.0_linux_amd64.tar.gz") | .digest)'
gh release download v1.35.0 -R oasdiff/oasdiff -p checksums.txt -O - | grep linux_amd64.tar.gz
gh api "repos/oasdiff/oasdiff/contents/internal/breaking_changes.go?ref=v1.35.0" --jq .content | base64 -d | grep -n 'Use:\|fail-on\|allow-external-refs'
```

Expected: `2026-10-28T16:31:43Z`; `sha256:a8023002fcb2eaa7f5758148a9303cb63d33b939886df312268bc0fc7b939140`; the
checksums line with the same hash; and `Use: "breaking base revision [flags]"`, the `fail-on` flag ("exit with return
code 1 when output includes errors with this level or higher") and the `allow-external-refs` flag. If any differs,
stop and report: the workflow pins these values. (Checked on 2026-11-20 while writing this plan; the archive holds
`LICENSE` and `oasdiff` at its root.)

- [ ] **Step 2: Write the failing tests**

Append to `scripts/test_check_slice.py`, above `if __name__ == "__main__":`:

```python
class ContractPinScopeTest(unittest.TestCase):
    """Plan 21 (F9): moving a vendored contract pin is planned work, inside a bundle whose MAY CHANGE names it."""

    PIN = {"contracts/orders-api/openapi.yaml": "openapi: 3.0.3\n", "contracts/orders-api/SOURCE": "tag: api-v1.1.0\n"}

    def test_a_pin_moved_outside_may_change_is_a_problem(self):
        r = Repo(bundle())
        r.commit("move the pin", self.PIN)
        self.assertEqual(r.check()[0], ["contracts/orders-api/SOURCE: outside every bundle's MAY CHANGE",
                                        "contracts/orders-api/openapi.yaml: outside every bundle's MAY CHANGE"])

    def test_a_pin_moved_in_its_own_slice_is_clean(self):
        r = Repo(bundle(may="src/**, tests/**, contracts/orders-api/**"))
        r.commit("move the pin", self.PIN)
        self.assertEqual(r.check(), ([], []))

    def test_a_pin_named_in_must_not_stays_out(self):
        r = Repo(bundle(may="**", must_not="AGENTS.md, contracts/**"))
        r.commit("move the pin", self.PIN)
        self.assertIn("contracts/orders-api/SOURCE: changed, but a bundle's MUST NOT names it", r.check()[0])
```

Append to `scripts/test_multirepo.py`, above `if __name__ == "__main__":`:

```python
class ContractWorkflowTest(unittest.TestCase):
    """F9: the provider publishes from its default branch and checks every change; the consumer checks its copy."""

    def setUp(self):
        self.check = read("starter/repo/.github/workflows/contract-check.yml")
        self.publish = read("starter/repo/.github/workflows/contract-publish.yml")
        self.ci = read("starter/repo/.github/workflows/ci.yml")

    def test_every_action_is_pinned_and_no_run_block_interpolates(self):
        for name, text in (("contract-check", self.check), ("contract-publish", self.publish), ("ci", self.ci)):
            self.assertEqual(pinned_uses(text), [], name)
            for block in run_blocks(text):
                self.assertNotIn("${{", block, name)

    def test_oasdiff_is_pinned_by_version_and_checksum(self):
        self.assertIn("OASDIFF_VERSION: 1.35.0", self.check)
        self.assertIn("OASDIFF_SHA256: a8023002fcb2eaa7f5758148a9303cb63d33b939886df312268bc0fc7b939140", self.check)
        self.assertIn("sha256sum -c -", self.check)
        script = read("starter/repo/scripts/check_contract_version.py")
        self.assertIn('"breaking", "--fail-on", "ERR", "--allow-external-refs=false"', script)

    def test_the_check_runs_the_base_branchs_script_read_only(self):
        self.assertIn('git show "origin/$BASE_REF:scripts/check_contract_version.py"', self.check)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", self.check)
        self.assertNotIn("contents: write", self.check)

    def test_only_the_publish_job_writes_and_only_from_main(self):
        self.assertEqual(self.publish.count("contents: write"), 1)
        self.assertIn("branches: [main]", self.publish)
        self.assertIn("--publish-tag", self.publish)
        self.assertIn("rulesets need a public repository on GitHub Free", " ".join(self.publish.split()))

    def test_ci_checks_the_vendored_contracts(self):
        self.assertIn("contract-pin:", self.ci)
        self.assertIn("python3 scripts/check_contract_pin.py", self.ci)

    def test_the_guide_names_the_commands(self):
        for rel in ("starter/repo/AGENTS.md", "skills/aidlc-onboard/assets/agents-md.md"):
            text = read(rel)
            self.assertIn("python3 scripts/check_contract_pin.py --update <provider> api-v<version>", text, rel)
            self.assertIn("python3 scripts/check_contract_version.py --contract <path>", text, rel)

    def test_the_session_cannot_edit_the_contract_scripts(self):
        deny = json.loads(read("starter/repo/.claude/settings.json"))["permissions"]["deny"]
        self.assertIn("Edit(/scripts/check_*.py)", deny)
```

- [ ] **Step 3: Run them**

Run: `python3 -m unittest scripts.test_check_slice.ContractPinScopeTest scripts.test_multirepo.ContractWorkflowTest -v`
Expected: the three `ContractPinScopeTest` tests PASS at once: they pin behaviour this plan relies on (a pin move is
in scope only when MAY CHANGE names it), with no change to `check_slice.py`. `ContractWorkflowTest` fails or errors
in all 7: its `setUp` reads the two workflows, which do not exist yet.

- [ ] **Step 4: Write the workflows**

Create `starter/repo/.github/workflows/contract-check.yml`:

```yaml
# The provider's contract check (aidlc ADR 0022; change list F9, decision D9). Keep this file in a repository that
# owns a contract; a consumer deletes it. Set CONTRACT to the path AGENTS.md names, and make "contract-check" a
# required check in branch protection (GitHub Free: public repositories only).
#
# It compares the pull request's contract with the last published version (the highest api-v* tag): a changed
# contract must raise info.version, and a breaking change must raise its MAJOR, with each consumer's agreement
# recorded in the pull request description, which the code owner checks. oasdiff is the release binary at a pinned
# version, checked against its published sha256 before it runs, and it never follows external $refs.
name: contract-check
on:
  pull_request:
permissions:
  contents: read
env:
  CONTRACT: openapi.yaml
  OASDIFF_VERSION: 1.35.0
  OASDIFF_SHA256: a8023002fcb2eaa7f5758148a9303cb63d33b939886df312268bc0fc7b939140
jobs:
  contract-check:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}
          persist-credentials: false
      - name: oasdiff, at a pinned version and checksum
        run: |
          curl -fsSL -o "$RUNNER_TEMP/oasdiff.tar.gz" \
            "https://github.com/oasdiff/oasdiff/releases/download/v${OASDIFF_VERSION}/oasdiff_${OASDIFF_VERSION}_linux_amd64.tar.gz"
          echo "${OASDIFF_SHA256}  $RUNNER_TEMP/oasdiff.tar.gz" | sha256sum -c -
          tar -xzf "$RUNNER_TEMP/oasdiff.tar.gz" -C "$RUNNER_TEMP" oasdiff
      - name: A changed contract raises its version; a breaking change raises MAJOR
        env:
          BASE_REF: ${{ github.base_ref }}
        run: |
          mkdir -p "$RUNNER_TEMP/aidlc"
          if git cat-file -e "origin/$BASE_REF:scripts/check_contract_version.py" 2>/dev/null; then
            git show "origin/$BASE_REF:scripts/check_contract_version.py" > "$RUNNER_TEMP/aidlc/check_contract_version.py"
          else
            cp scripts/check_contract_version.py "$RUNNER_TEMP/aidlc/check_contract_version.py"
          fi
          python3 "$RUNNER_TEMP/aidlc/check_contract_version.py" --contract "$CONTRACT" --oasdiff "$RUNNER_TEMP/oasdiff"
```

Create `starter/repo/.github/workflows/contract-publish.yml`:

```yaml
# Publishes the provider's contract (aidlc ADR 0022; change list F9). On every push to the default branch, it tags
# the commit api-v<info.version> when that version is not published yet, so a version exists only once it passed
# review and the contract-check on its pull request. A consumer pins that tag. Set CONTRACT to the path AGENTS.md
# names; a consumer deletes this file. Only this job may write, and only tags.
#
# A published version never changes. Protect the tags with a ruleset on "api-v*" that blocks updates and deletions
# (rulesets need a public repository on GitHub Free, or a Pro or Team plan); the consumers' online pin check reports
# a tag that moved either way.
name: contract-publish
on:
  push:
    branches: [main]
permissions:
  contents: read
concurrency: {group: contract-publish, cancel-in-progress: false}
env:
  CONTRACT: openapi.yaml
jobs:
  contract-publish:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 0
      - name: Tag a new contract version
        run: |
          TAG="$(python3 scripts/check_contract_version.py --contract "$CONTRACT" --publish-tag)"
          if [ -z "$TAG" ]; then
            echo "no new contract version to publish"
            exit 0
          fi
          git tag "$TAG" "$GITHUB_SHA"
          git push origin "refs/tags/$TAG"
          echo "published $TAG"
```

Append to `starter/repo/.github/workflows/ci.yml`, after the last line of the `slice-check` job:

```yaml
  # A consumer's vendored contracts (contracts/<provider>/) match their SOURCE: the published tag, its commit and the
  # copy's sha256 (aidlc ADR 0022). Offline, so the check never needs the provider. A repository with no contracts/
  # passes. Make "contract-pin" a required check where the repository consumes a contract.
  contract-pin:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with: {persist-credentials: false}
      - name: Vendored contracts match their SOURCE
        run: |
          if [ -f scripts/check_contract_pin.py ]; then
            python3 scripts/check_contract_pin.py
          else
            echo "no contract pin check in this repository"
          fi
```

- [ ] **Step 5: The guide names the commands**

In `starter/repo/AGENTS.md`, replace:

```markdown
- Plan check, before asking for the plan's approval: `python3 scripts/check_plan.py <KEY> [--part <n>]`
```

with:

```markdown
- Plan check, before asking for the plan's approval: `python3 scripts/check_plan.py <KEY> [--part <n>]`
- Contract pin, a consumer's vendored contracts match their SOURCE (CI runs it too): `python3 scripts/check_contract_pin.py`;
  move a pin only to a published tag, in its own slice: `python3 scripts/check_contract_pin.py --update <provider> api-v<version>`
- Contract check, a provider's contract against its last published tag (CI runs it with oasdiff):
  `python3 scripts/check_contract_version.py --contract <path> --oasdiff <oasdiff binary>`
```

In `skills/aidlc-onboard/assets/agents-md.md`, replace:

```markdown
- Plan check, before asking for the plan's approval: `python3 scripts/check_plan.py <KEY> [--part <n>]`
```

with:

```markdown
- Plan check, before asking for the plan's approval: `python3 scripts/check_plan.py <KEY> [--part <n>]`
- Contract pin, a consumer's vendored contracts match their SOURCE (CI runs it too): `python3 scripts/check_contract_pin.py`;
  move a pin only to a published tag, in its own slice: `python3 scripts/check_contract_pin.py --update <provider> api-v<version>`
- Contract check, a provider's contract against its last published tag (CI runs it with oasdiff):
  `python3 scripts/check_contract_version.py --contract <path> --oasdiff <oasdiff binary>`
```

In `starter/repo/AGENTS.md`, replace:

```markdown
- Owners: <CODEOWNERS path>
```

with:

```markdown
- Owners: <CODEOWNERS path>
- Contract: <path of the OpenAPI file this repository owns, published as tags api-v<version>> | <none>; copies of
  other repositories' contracts: `contracts/<provider>/`, read-only, each with its SOURCE
```

In `skills/aidlc-onboard/assets/agents-md.md`, replace:

```markdown
- Owners: {{CODEOWNERS path}}
```

with:

```markdown
- Owners: {{CODEOWNERS path}}
- Contract: {{path of the OpenAPI file this repository owns, or none}}, published as tags `api-v{{version}}`; copies
  of other repositories' contracts: `contracts/{{provider}}/`, read-only, each with its SOURCE
```

- [ ] **Step 6: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_check_slice scripts.test_multirepo scripts.test_gates_hold -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; the suite is 612, OK. `WiringTest.test_ci_runs_the_base_branchs_copy_on_the_head_commit` and
`FinalReviewFixesTest` still pass: the `slice-check` job is unchanged, and the new job has no `${{ }}` in `run:`.

- [ ] **Step 7: Commit**

```bash
git add starter/repo/.github/workflows/contract-check.yml starter/repo/.github/workflows/contract-publish.yml starter/repo/.github/workflows/ci.yml starter/repo/AGENTS.md skills/aidlc-onboard/assets/agents-md.md scripts/test_check_slice.py scripts/test_multirepo.py
git commit -m "feat(starter): contract-check and contract-publish workflows for providers; a contract-pin job for consumers (F9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 8: Templates: the pin, the criteria copy, the ADR scope, the story folder (F3, F4, F5, F13)

**Files:**
- Modify: `skills/aidlc-start/assets/story-index.md` and `skills/aidlc-plan/assets/story-index.md` (identical edits:
  `test_handoffs` keeps them equal), `skills/aidlc-plan/assets/task-bundle.md`, `skills/aidlc-design/assets/adr.md`,
  `skills/aidlc-design/assets/coordination-plan.md`, `skills/aidlc-design/assets/new-system.md`
- Create: `skills/aidlc-plan/assets/criteria.md`
- Modify: `skills/aidlc-plan/SKILL.md` (front matter: `templates` lists `criteria`)
- Modify: `starter/workspace/stories/README.md`
- Test: `scripts/test_multirepo.py` (new class `TemplateTest`)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_multirepo.py`, above `if __name__ == "__main__":`:

```python
class TemplateTest(unittest.TestCase):
    """F3, F4, F5, F13: the templates carry the pin, the criteria copy, the ADR scope and permalinks."""

    def test_the_part_index_and_the_bundle_pin_the_home_commit(self):
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/task-bundle.md"):
            self.assertIn("spec v<n> @ <home commit>", read(rel), rel)
        self.assertIn("GitHub permalinks at a commit", flat("skills/aidlc-start/assets/story-index.md"))

    def test_the_criteria_copy_names_its_source(self):
        text = read("skills/aidlc-plan/assets/criteria.md")
        self.assertIn("## For the reviewer", text)
        self.assertIn("```text\nSOURCE     {{home repository}} stories/{{KEY}}/spec.md @ {{home commit}}", text)
        for heading in ("## Acceptance criteria", "## Edge cases", "## Non-goals"):
            self.assertIn(heading, text)
        self.assertIn("  - criteria\n", read("skills/aidlc-plan/SKILL.md"))

    def test_adrs_carry_their_scope_and_draft_name(self):
        self.assertIn("Scope: {{one repository", read("skills/aidlc-design/assets/adr.md"))
        self.assertIn("`{{KEY}}-adr-{{n}}.md`", read("skills/aidlc-design/assets/adr.md"))
        self.assertNotIn("adr-draft", read("starter/workspace/stories/README.md") + read("skills/aidlc-design/assets/new-system.md"))

    def test_the_coordination_plan_names_the_pins(self):
        self.assertIn("api-v<version> in contracts/<provider>/SOURCE", read("skills/aidlc-design/assets/coordination-plan.md"))

    def test_the_story_folder_says_who_owns_each_fact(self):
        text = flat("starter/workspace/stories/README.md")
        self.assertIn("## Who owns each fact (ADR 0022)", text)
        self.assertIn("`plans/<KEY>/criteria.md`", text)
        self.assertIn("nothing under `stories/<KEY>/` is moved or renamed", text)
```

- [ ] **Step 2: Run them to see them fail.** Run: `python3 -m unittest scripts.test_multirepo.TemplateTest -v`. Expected: FAIL in all 5.

- [ ] **Step 3: Edit the templates**

In `skills/aidlc-start/assets/story-index.md`, replace:

```markdown
PINS       spec v<n> · plan v<n> · contract <name> v<n>        (a part: what its latest bundle builds on; a story leaves this line out)
```

with:

```markdown
PINS       spec v<n> @ <home commit> · plan v<n> · contract <name> v<n>        (a part: what its latest bundle builds on, the spec at the home repository's commit; a story leaves this line out)
```

In `skills/aidlc-start/assets/story-index.md`, replace:

```markdown
the default branch only through the merge. A re-plan or a revision resets the later rows to "to do".
```

with:

```markdown
the default branch only through the merge. A re-plan or a revision resets the later rows to "to do". The story
status command checks the merged row against the real merge state and reports a row that disagrees.

Links to these documents on the tracker are GitHub permalinks at a commit (`/blob/<commit>/`), never a branch
path, which moves.
```

In `skills/aidlc-plan/assets/story-index.md`, replace:

```markdown
PINS       spec v<n> · plan v<n> · contract <name> v<n>        (a part: what its latest bundle builds on; a story leaves this line out)
```

with:

```markdown
PINS       spec v<n> @ <home commit> · plan v<n> · contract <name> v<n>        (a part: what its latest bundle builds on, the spec at the home repository's commit; a story leaves this line out)
```

In `skills/aidlc-plan/assets/story-index.md`, replace:

```markdown
the default branch only through the merge. A re-plan or a revision resets the later rows to "to do".
```

with:

```markdown
the default branch only through the merge. A re-plan or a revision resets the later rows to "to do". The story
status command checks the merged row against the real merge state and reports a row that disagrees.

Links to these documents on the tracker are GitHub permalinks at a commit (`/blob/<commit>/`), never a branch
path, which moves.
```

In `skills/aidlc-plan/assets/task-bundle.md`, replace:

```markdown
PINS        spec v<n> · plan v<n> · contract <name> v<n> | contract none
```

with:

```markdown
PINS        spec v<n> @ <home commit> · plan v<n> · contract <name> v<n> | contract none   (@ <home commit>: a part of a story across several repositories)
```

Create `skills/aidlc-plan/assets/criteria.md`:

````markdown
<!-- aidlc template: criteria -->
# {{KEY}} · part {{PART}} · acceptance criteria (read-only copy)

## For the reviewer
- **Asked of:** The tech lead, with the plan: that this copy holds the part's own criteria and non-goals, word for word
- **Record it:** With the plan's approval on the work item; the copy changes only when the plan does
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

This is a copy. The spec in the home repository is the original, and only its owner changes it. The part's CI, its
reviewers and its AI review read this copy, so they never need the home repository. The story status command reports
any line here that is not in the spec at the commit below.

```text
SOURCE     {{home repository}} stories/{{KEY}}/spec.md @ {{home commit}} (spec v{{n}})
```

## Acceptance criteria
{{each criterion this part's tests prove, copied word for word with its Given, When and Then lines}}

## Edge cases
{{each edge case this part handles, copied word for word with its decided behaviour and its decider}}

## Non-goals
{{the spec's Non-goals line, copied word for word}}
````

In `skills/aidlc-design/assets/adr.md`, replace:

```markdown
Decider: {{name/role}} · Agreed: {{owners and consumers}} · Work item: {{key}} · Tier: {{n}}
```

with:

```markdown
Decider: {{name/role}} · Agreed: {{owners and consumers}} · Work item: {{key}} · Tier: {{n}}
Scope: {{one repository: it moves to that repository's docs/adr/ | several repositories: it stays in the home repository's docs/adr/, and each affected repository gets a one-line ADR that links it at a commit}} · Draft: `{{KEY}}-adr-{{n}}.md`
```

In `skills/aidlc-design/assets/coordination-plan.md`, replace:

```markdown
CONTRACTS  <contract> v<n> <from> -> <to> (<minor, additive | major via expand and contract>)
```

with:

```markdown
CONTRACTS  <contract> v<n> <from> -> <to> (<minor, additive | major via expand and contract>)
PINS       Each part pins spec v<n> @ <home commit>; each consumer pins the provider's published tag
           api-v<version> in contracts/<provider>/SOURCE (ADR 0022)
```

In `skills/aidlc-design/assets/new-system.md`, replace:

```markdown
ADR: <adr-draft-n.md>
```

with:

```markdown
ADR: <KEY-adr-n.md>
```

In `skills/aidlc-plan/SKILL.md`, replace:

```markdown
  - feature-brief
  references:
```

with:

```markdown
  - feature-brief
  - criteria
  references:
```

In `starter/workspace/stories/README.md`, replace:

```markdown
| `design-note.md`, `adr-draft-<n>.md`, `contract/` | `aidlc-design` | The decisions, ADR drafts and the drafted contract change (accepted ADRs move to the repository each one governs) |
```

with:

```markdown
| `design-note.md`, `<KEY>-adr-<n>.md`, `contract/` | `aidlc-design` | The decisions, ADR drafts and the drafted contract change (an accepted ADR that governs one repository moves there; one across repositories stays in the home repository's `docs/adr/`) |
```

In `starter/workspace/stories/README.md`, replace:

```markdown
Each repository keeps its own part's plan, task bundles, evidence and review record in its `plans/<KEY>/`.
```

with:

```markdown
Each repository keeps its own part's plan, task bundles, evidence and review record in its `plans/<KEY>/`.

## Who owns each fact (ADR 0022)

Each fact has one owner, and only the owner changes it. The others read it at a version and a commit.

| Here, in the home repository (`stories/<KEY>/`, `docs/adr/`, `incidents/`) | In each part's repository |
|---|---|
| The index, intent, spec, evidence pack, design note, ADR drafts and the contract draft | The plan, the task bundles and the progress notes |
| The coordination plan and `status.md` | `plans/<KEY>/criteria.md`: a read-only copy of the part's criteria, with the home commit it came from |
| The release records and incidents | The evidence, the pull request description and the review record |
| ADRs across repositories | ADRs that govern only that repository, and the code |
| | The published contract, in the provider (tag `api-v<version>`); each consumer's read-only copy in `contracts/<provider>/` |

A part pins the spec as `spec v<n> @ <commit>`. Once a part pins it, nothing under `stories/<KEY>/` is moved or
renamed: a change is a new version.
```

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_multirepo scripts.test_handoffs scripts.test_routes -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; the suite is 617, OK. `test_handoffs` checks the new template too (`test_every_fence_is_a_text_fence`,
`test_no_template_has_a_placeholder_that_vanishes`, `test_m1_every_template_keeps_the_rule`), and still finds the two
story-index copies identical.

- [ ] **Step 5: Commit**

```bash
git add skills/aidlc-start/assets/story-index.md skills/aidlc-plan/assets/story-index.md skills/aidlc-plan/assets/task-bundle.md skills/aidlc-plan/assets/criteria.md skills/aidlc-plan/SKILL.md skills/aidlc-design/assets/adr.md skills/aidlc-design/assets/coordination-plan.md skills/aidlc-design/assets/new-system.md starter/workspace/stories/README.md scripts/test_multirepo.py
git commit -m "feat(skills): templates pin the home commit, copy the part's criteria and file ADRs by scope (F3, F4, F5, F13)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 9: The stages place each fact with its owner and read the criteria copy (F2, F3, F4, F5)

**Files:**
- Modify: `skills/aidlc-design/SKILL.md` (step 5; Produces), `skills/aidlc-plan/SKILL.md` (steps 7 and 8),
  `skills/aidlc-verify/SKILL.md` (Inputs), `skills/aidlc-review/SKILL.md` (Inputs), `skills/aidlc-build/SKILL.md`
  (Inputs), `agents/reviewer-compliance.md` (one bullet)
- Test: `scripts/test_multirepo.py` (new class `PlacementTest`)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_multirepo.py`, above `if __name__ == "__main__":`:

```python
class PlacementTest(unittest.TestCase):
    """F2, F3, F4, F5: the stages place each fact with its owner and read the criteria copy."""

    def test_design_places_each_fact_and_files_adrs_by_scope(self):
        design = skill("aidlc-design")
        self.assertIn("Each fact has one owner, and only the owner changes it (ADR 0022)", design)
        self.assertIn("Name the draft `<KEY>-adr-<n>.md` and fill its Scope", design)
        self.assertIn("each affected repository gets a one-line ADR that links it at the home commit", design)
        self.assertNotIn("adr-draft", design)

    def test_plan_pins_the_home_commit_and_writes_the_copy(self):
        plan = skill("aidlc-plan")
        self.assertIn("`spec v<n> @ <commit>`", plan)
        self.assertIn("nothing under `stories/<KEY>/` is moved or renamed", plan)
        self.assertIn("write `plans/<KEY>/criteria.md` from `assets/criteria.md`", plan)

    def test_verify_review_build_and_compliance_read_the_copy(self):
        for rel in ("skills/aidlc-verify/SKILL.md", "skills/aidlc-review/SKILL.md", "skills/aidlc-build/SKILL.md",
                    "agents/reviewer-compliance.md"):
            self.assertIn("`plans/<KEY>/criteria.md`", flat(rel), rel)
        self.assertIn("names the same commit on its SOURCE line", flat("agents/reviewer-compliance.md"))
```

- [ ] **Step 2: Run them to see them fail.** Run: `python3 -m unittest scripts.test_multirepo.PlacementTest -v`. Expected: FAIL in all 3.

- [ ] **Step 3: Edit the skills and the agent**

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
5. Draft the ADR from `assets/adr.md` with status Proposed, the named decider, and the consumers who must agree.
```

with:

```markdown
5. Draft the ADR from `assets/adr.md` with status Proposed, the named decider, and the consumers who must agree. Name the draft `<KEY>-adr-<n>.md` and fill its Scope: a decision that governs one repository moves into that repository's `docs/adr/` once accepted; a decision across repositories stays in the home repository's `docs/adr/`, and each affected repository gets a one-line ADR that links it at the home commit (ADR 0022).
```

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
its decision frames; one `adr-draft-<n>.md` per decision, which its owner moves into the governed repository's ADR
folder once it is accepted;
```

with:

```markdown
its decision frames; one `<KEY>-adr-<n>.md` per decision, which its owner files by its Scope once it is accepted
(step 5);
```

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
tests, which the contract's owner applies; and, for a story across several repositories, `coordination-plan.md`.
```

with:

```markdown
tests, which the contract's owner applies; and, for a story across several repositories, `coordination-plan.md`.

Each fact has one owner, and only the owner changes it (ADR 0022). For a story across several repositories, the
home repository (the workspace root) holds the index, intent, spec, design note, ADR drafts, contract draft,
coordination plan, status, release records and incidents. Each part's repository holds its plan, bundles, criteria
copy, progress notes, evidence, pull request description, review record, its own ADRs and its code; the provider
holds the published contract.
```

In `skills/aidlc-plan/SKILL.md`, replace:

```markdown
   - pin the spec, plan and contract versions in PINS, and copy that line into the part index;
```

with:

```markdown
   - pin the spec, plan and contract versions in PINS, and copy that line into the part index. For a part of a story
     across several repositories, the spec pin also names the home repository's commit where the approved spec
     merged: `spec v<n> @ <commit>`. Once a part pins it, nothing under `stories/<KEY>/` is moved or renamed; a
     change is a new version (ADR 0022);
```

In `skills/aidlc-plan/SKILL.md`, replace:

```markdown
   latest bundle, and the rows `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review` and `merged`.
```

with:

```markdown
   latest bundle, and the rows `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review` and `merged`. Beside it,
   write `plans/<KEY>/criteria.md` from `assets/criteria.md`: the part's own criteria, edge cases and non-goals,
   copied word for word from the spec at the pinned commit, under a SOURCE line naming the home repository, the
   spec's path and that commit. The copy is read-only: the part's CI and reviewers read it instead of the home
   repository, and the story status command reports a copy that differs from the spec (ADR 0022).
```

In `skills/aidlc-verify/SKILL.md`, replace:

```markdown
On route F0, the feature brief `plans/<KEY>/brief.md` (its CRITERIA lines, each mapped to its test) in place of the spec and the plan.
```

with:

```markdown
On route F0, the feature brief `plans/<KEY>/brief.md` (its CRITERIA lines, each mapped to its test) in place of the spec and the plan. For a part of a story across several repositories, the criteria are the part's read-only copy `plans/<KEY>/criteria.md`, which names the home commit it came from: the trusted run never needs the home repository.
```

In `skills/aidlc-review/SKILL.md`, replace:

```markdown
and, if the tool keeps one, the session's log of the agent's tool calls, which the person supplies (the security review's TOOLS row needs it).
```

with:

```markdown
and, if the tool keeps one, the session's log of the agent's tool calls, which the person supplies (the security review's TOOLS row needs it). For a part of a story across several repositories, read the criteria from the read-only copy `plans/<KEY>/criteria.md`, whose SOURCE line names the home commit, so the review never needs the home repository.
```

In `skills/aidlc-build/SKILL.md`, replace:

```markdown
the spec and plan versions it pins, and the branch's earlier commits
```

with:

```markdown
the spec and plan versions it pins (for a part of a story across several repositories, the criteria are the read-only copy `plans/<KEY>/criteria.md`), and the branch's earlier commits
```

In `agents/reviewer-compliance.md`, replace:

```markdown
- The bundle's PINS match the spec, plan and contract versions the change builds on.
```

with:

```markdown
- The bundle's PINS match the spec, plan and contract versions the change builds on.
- For a part of a story across several repositories, the spec pin names a home commit (`spec v<n> @ <commit>`),
  `plans/<KEY>/criteria.md` names the same commit on its SOURCE line, and the criteria you check come from that
  copy. A copy under `contracts/<provider>/` changes only in a slice whose MAY CHANGE names it, together with its
  SOURCE.
```

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_multirepo scripts.test_routes scripts.test_loads -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; the suite is 620, OK. `test_routes` still finds "pin the spec, plan and contract versions", the
part-index rows and "except the part index's rows and its PINS line"; `test_loads` finds no new load; the validator
resolves `assets/criteria.md`.

- [ ] **Step 5: Commit**

```bash
git add skills/aidlc-design/SKILL.md skills/aidlc-plan/SKILL.md skills/aidlc-verify/SKILL.md skills/aidlc-review/SKILL.md skills/aidlc-build/SKILL.md agents/reviewer-compliance.md scripts/test_multirepo.py
git commit -m "feat(skills): each fact has one owner; parts pin the home commit and read their criteria copy (F2-F5, ADR 0022)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 10: One repository when code ships together; Decision 2; permalinks; status; onboarding (F1, F6, F11, F13, F14)

**Files:**
- Modify: `skills/aidlc-onboard/SKILL.md` (step 0, step 5), `skills/aidlc-design/SKILL.md` (new system step 1;
  Gate), `skills/aidlc-plan/SKILL.md` (Gate), `skills/aidlc-start/SKILL.md` (steps 6 and 7),
  `skills/aidlc-specify/SKILL.md` (step 7), `skills/aidlc-release/SKILL.md` (step 1)
- Test: `scripts/test_multirepo.py` (new class `DecisionsTest`)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_multirepo.py`, above `if __name__ == "__main__":`:

```python
class DecisionsTest(unittest.TestCase):
    """F1, F6, F11, F13, F14: one repository when code ships together, Decision 2, permalinks and status."""

    def test_code_that_ships_together_goes_in_one_repository(self):
        self.assertIn("Code that ships together goes in one repository (ADR 0022)", skill("aidlc-onboard"))
        self.assertIn("Recommend one repository for code that ships together (ADR 0022)", skill("aidlc-design"))
        self.assertIn("code that ships together belongs in one repository (ADR 0022)", skill("aidlc-start"))

    def test_decision_2_across_repositories_is_two_pull_requests(self):
        self.assertIn("Decision 2 (design and plan) is this design's pull request in the home repository, then each "
                      "part's plan pull request in its own repository", gate("aidlc-design"))
        self.assertIn("Decision 2 is the home design pull request plus this plan's pull request, titled "
                      "`[<KEY>] part <n> of <m>, plan v<n>: <what>`", gate("aidlc-plan"))

    def test_tracker_links_are_permalinks(self):
        self.assertIn("GitHub permalink at a commit", skill("aidlc-start"))
        self.assertIn("Link the spec by its GitHub permalink at the commit where it merged", skill("aidlc-specify"))

    def test_release_reads_the_real_merge_state(self):
        self.assertIn("takes each part's merge state from its pull request on GitHub when it can", skill("aidlc-release"))

    def test_onboard_sets_up_the_home_repository(self):
        onboard = skill("aidlc-onboard")
        self.assertIn("copy `CODEOWNERS` from aidlc's `starter/workspace/` to `.github/CODEOWNERS`", onboard)
        self.assertIn("run `python3 scripts/story_status.py --write-gitignore`", onboard)
        self.assertIn("propose `check_contract_pin.py` with `check_contract_version.py`, which it imports", onboard)
```

- [ ] **Step 2: Run them to see them fail.** Run: `python3 -m unittest scripts.test_multirepo.DecisionsTest -v`. Expected: FAIL in all 5.

- [ ] **Step 3: Edit the skills**

In `skills/aidlc-onboard/SKILL.md`, replace:

```markdown
0. Where am I? At a workspace root (a folder holding several repositories): write `WORKSPACE.md` from
```

with:

```markdown
0. Where am I? At a workspace root (a folder holding several repositories): first ask whether these repositories must stay separate. Code that ships together goes in one repository (ADR 0022); a workspace is for repositories with different owners, release cycles or runtimes. The workspace root is a git repository of its own, the home repository: the story status command's pin and criteria checks read its history. Then write `WORKSPACE.md` from
```

In `skills/aidlc-onboard/SKILL.md`, replace:

```markdown
copy `story_status.py` from aidlc's `starter/workspace/scripts/` into the workspace's `scripts/` folder, and,
```

with:

```markdown
copy `story_status.py` from aidlc's `starter/workspace/scripts/` into the workspace's `scripts/` folder, copy `CODEOWNERS` from aidlc's `starter/workspace/` to `.github/CODEOWNERS` (the leads own `stories/**`; the runtime environment's owner owns its compose files and flags), run `python3 scripts/story_status.py --write-gitignore`, which writes the root's `.gitignore` from the repository table in `WORKSPACE.md`, and,
```

In `skills/aidlc-onboard/SKILL.md`, replace:

```markdown
and ask the person to add its deny rule to `.claude/settings.json` (a session cannot edit it).
```

with:

```markdown
and ask the person to add its deny rule to `.claude/settings.json` (a session cannot edit it). Run `python3 scripts/story_status.py --write-gitignore` again whenever the repository table changes.
```

In `skills/aidlc-onboard/SKILL.md`, replace:

```markdown
Say which controls hold in the team's tool and on its GitHub plan ("Where the gates hold" in the README): on GitHub Free, required checks and branch protection work only on public repositories.
```

with:

```markdown
Say which controls hold in the team's tool and on its GitHub plan ("Where the gates hold" in the README): on GitHub Free, required checks and branch protection work only on public repositories. When the repository owns a contract that other repositories use, propose `contract-check.yml`, `contract-publish.yml` and `check_contract_version.py`, and name the contract's path in `AGENTS.md`; when it consumes one, propose `check_contract_pin.py` with `check_contract_version.py`, which it imports (ADR 0022).
```

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
   that slice 0 runs. Write one REPOSITORY block per repository: its stack, dependencies, paths, commands, scaffold and CI.
```

with:

```markdown
   that slice 0 runs. Write one REPOSITORY block per repository: its stack, dependencies, paths, commands, scaffold and CI.
   Recommend one repository for code that ships together (ADR 0022); choose several only for a stated reason
   (different owners, release cycles or runtimes), recorded in an ADR draft.
```

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
which the tech lead or architect approves (ADR 0020). You draft; you never approve.
```

with:

```markdown
which the tech lead or architect approves (ADR 0020). For a story across several repositories, Decision 2 (design and plan) is this design's pull request in the home repository, then each part's plan pull request in its own repository; a part plans only from the merged design (ADR 0022). You draft; you never approve.
```

In `skills/aidlc-plan/SKILL.md`, replace:

```markdown
the code owner approves it with the change in the pull request. You draft; you never approve.
```

with:

```markdown
the code owner approves it with the change in the pull request. For a part of a story across several repositories, Decision 2 is the home design pull request plus this plan's pull request, titled `[<KEY>] part <n> of <m>, plan v<n>: <what>`, so the story status command never reads it as the part's code (ADR 0022). You draft; you never approve.
```

In `skills/aidlc-start/SKILL.md`, replace:

```markdown
   repository, `stories/<KEY>/README.md` at a workspace root. Fill SOURCE, KIND, ROUTE and LEVEL, and one row per stage
   of the route with where it runs and the status "to do".
```

with:

```markdown
   repository, `stories/<KEY>/README.md` at a workspace root. Fill SOURCE, KIND, ROUTE and LEVEL, and one row per stage
   of the route with where it runs and the status "to do". A link to a story document that goes on the tracker is a
   GitHub permalink at a commit (`https://github.com/<org>/<repository>/blob/<commit>/stories/<KEY>/spec.md`), never
   a branch path, which moves.
```

In `skills/aidlc-start/SKILL.md`, replace:

```markdown
documents in `stories/<KEY>/`; each repository's part runs inside that repository. A story across several repositories is at least Tier 2 (`assets/tiers.md`).
```

with:

```markdown
documents in `stories/<KEY>/`; each repository's part runs inside that repository. A story across several repositories is at least Tier 2 (`assets/tiers.md`). When those repositories always ship together, tell the tech lead: code that ships together belongs in one repository (ADR 0022).
```

In `skills/aidlc-specify/SKILL.md`, replace:

```markdown
7. Offer to post the criteria as a comment on the work item, for the product owner to put in the story. Posting asks the person first.
```

with:

```markdown
7. Offer to post the criteria as a comment on the work item, for the product owner to put in the story. Posting asks the person first. Link the spec by its GitHub permalink at the commit where it merged, never by a branch path.
```

In `skills/aidlc-release/SKILL.md`, replace:

```markdown
every part must be merged at the current versions. A part that pins an older spec
```

with:

```markdown
every part must be merged at the current versions. The command takes each part's merge state from its pull request on GitHub when it can, else from the default branch's copy of the part index, and reports a hand-marked row that disagrees, a pin that drifted from the home repository and a criteria copy that differs from the spec. A part that pins an older spec
```

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_multirepo scripts.test_gates_hold scripts.test_handoffs scripts.test_greenfield scripts.test_one_plugin -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; the suite is 625, OK. These pinned sentences still hold: onboard's "copy `.claude/settings.json`
last", "add one deny rule per repository, `Edit(/<repository>/**)`, to the settings before you copy them in" and
"ask the person to add its deny rule to `.claude/settings.json`"; the Gates' "merges to the default branch first, in
its own pull request", "records the approval on the work item with the plan's version and commit" and the
reviewer-block names (`test_each_decision_block_matches_its_gate`); start's step numbers
(`test_start_steps_are_numbered_in_order`).

- [ ] **Step 5: Commit**

```bash
git add skills/aidlc-onboard/SKILL.md skills/aidlc-design/SKILL.md skills/aidlc-plan/SKILL.md skills/aidlc-start/SKILL.md skills/aidlc-specify/SKILL.md skills/aidlc-release/SKILL.md scripts/test_multirepo.py
git commit -m "feat(skills): one repository when code ships together; Decision 2 across repositories; permalinks; real merge state (F1, F6, F11, F13, F14)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 11: The contract guidance: designing-apis and design's amendment mode (F9)

**Files:**
- Modify: `skills/designing-apis/SKILL.md` (new section before "## REST API Patterns"; one Red Flag; one
  Verification item), `skills/aidlc-design/SKILL.md` (step 6; amendment steps 2 and 3)
- Test: `scripts/test_multirepo.py` (new class `ContractGuidanceTest`)

`designing-apis` is one of the eight earlier practices (adapted, `skills/NOTICE`). The new section is in original
words and keeps the skill's own structure; `EARLIER_PRACTICES` in the validator is unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_multirepo.py`, above `if __name__ == "__main__":`:

```python
class ContractGuidanceTest(unittest.TestCase):
    """F9: designing-apis teaches the rule; design's amendment mode follows the tags and pins."""

    def test_designing_apis_teaches_the_spec_kit_rule(self):
        text = flat("skills/designing-apis/SKILL.md")
        self.assertIn("## A Contract Across Repositories", read("skills/designing-apis/SKILL.md"))
        for phrase in ("`api-v<info.version>`", "Consumers pin a copy", "never \"latest\"", "Propose changes at the source",
                       "Pact and its `can-i-deploy` check"):
            self.assertIn(phrase, text, phrase)

    def test_the_amendment_follows_tags_and_pins(self):
        design = skill("aidlc-design")
        self.assertIn("its default branch publishes the tag `api-v<version>`", design)
        self.assertIn("Never point a consumer at an unpublished version", design)
        self.assertIn("The provider's contract check (oasdiff against the last published tag) must agree", design)
```

- [ ] **Step 2: Run them to see them fail.** Run: `python3 -m unittest scripts.test_multirepo.ContractGuidanceTest -v`. Expected: FAIL in both.

- [ ] **Step 3: Edit the practice and the stage**

In `skills/designing-apis/SKILL.md`, replace:

```markdown
## REST API Patterns
```

with:

```markdown
## A Contract Across Repositories

When another repository depends on your API, the contract is a versioned artifact with one owner. The provider owns
it; every consumer reads an exact published version. This is the contract-driven rule of GitHub's Spec Kit.

- **One file, one owner.** The provider keeps one OpenAPI file and names its path in `AGENTS.md`. Only the provider's
  reviewed pull requests change it.
- **Publish from the default branch only.** Each version is the git tag `api-v<info.version>`, created after the merge
  (the starter's `contract-publish.yml`). Never tag a branch by hand: a consumer could build on a version nobody
  reviewed.
- **Every change raises the version.** An additive change raises MINOR. A breaking change raises MAJOR, only with every
  consumer's agreement, done by expand and contract. The provider's `contract-check` runs oasdiff against the last
  published tag and fails a breaking change without a new MAJOR, and any change without a new version.
- **Consumers pin a copy.** Each consumer keeps a read-only copy in `contracts/<provider>/`, beside a `SOURCE` file
  naming the repository, tag, commit, path and sha256. Its CI checks the copy offline, so it never needs the
  provider. It moves the pin only to a named version (`--update <provider> api-v<version>`, never "latest"), in a
  slice of its own.
- **Test against the copy.** The consumer's client types and test fakes come from the vendored copy: generate the
  types from it, or validate each fake request and response against it with the OpenAPI validator the project already
  uses. Adding a validator is a new dependency: ask first. A fake that drifts from the contract then fails a test.
- **Propose changes at the source.** A consumer that needs a change asks for an amendment to the provider's contract
  (`aidlc-design`, amendment mode). It never edits its copy.

When many services depend on each other and pinned copies become hard to keep in step, consumer-driven contract
testing with a broker (Pact and its `can-i-deploy` check) is the next step; adopt it by an ADR.

## REST API Patterns
```

In `skills/designing-apis/SKILL.md`, replace:

```markdown
- [ ] Key retention is longer than the longest retry path, including dead-letter replay
```

with:

```markdown
- [ ] Key retention is longer than the longest retry path, including dead-letter replay
- [ ] A contract other repositories use is published as a tag from the default branch, and each consumer pins a
      copy with its SOURCE
```

In `skills/designing-apis/SKILL.md`, replace:

```markdown
- A key retention window shorter than the longest path that could re-deliver the request
```

with:

```markdown
- A key retention window shorter than the longest path that could re-deliver the request
- A consumer that reads a provider's contract from its default branch, or edits its vendored copy
```

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
Load the `designing-apis` skill for the contract, and load the `writing-tests` skill for its tests.
```

with:

```markdown
Load the `designing-apis` skill for the contract, and load the `writing-tests` skill for its tests. The provider owns the contract file its AGENTS.md names; consumers read it only at a published tag.
```

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
   breaking (major, done by expand and contract).
```

with:

```markdown
   breaking (major, done by expand and contract). The provider's contract check (oasdiff against the last
   published tag) must agree with that classification.
```

In `skills/aidlc-design/SKILL.md`, replace:

```markdown
3. The consumers approve the new version on the tracker. Record it in the ADR and in the story index's CURRENT line.
```

with:

```markdown
3. The consumers approve the new version on the tracker. Record it in the ADR and in the story index's CURRENT line.
   Once the provider's pull request merges, its default branch publishes the tag `api-v<version>`. Each consumer
   moves its copy to that tag with the contract pin command named in its AGENTS.md, in a slice whose MAY CHANGE
   names `contracts/<provider>/**`. Never point a consumer at an unpublished version.
```

- [ ] **Step 4: Run the tests and the suite**

Run: `python3 -m unittest scripts.test_multirepo scripts.test_routes scripts.test_loads -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`
Expected: PASS; the suite is 627, OK. `test_design_amends_a_contract_at_the_story_level` still finds "consumers
approve the new version", "CURRENT line" and "run in the provider's CI"; `test_loads` still finds exactly design's
loads (the edit keeps "Load the `designing-apis` skill" once).

- [ ] **Step 5: Commit**

```bash
git add skills/designing-apis/SKILL.md skills/aidlc-design/SKILL.md scripts/test_multirepo.py
git commit -m "docs(skills): a contract across repositories is published by tag and pinned by copy; Pact is the next step (F9)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 12: The map, the change list and the verification record

**Files:**
- Modify: `docs/codebase-map.md` (the starter line), `docs/design/2026-11-19-aidlc-6-change-list.md` (status line)
- Create: `docs/verification/2026-11-20-plan-21.md`
- Test: `scripts/test_multirepo.py` (new class `RecordTest`)

- [ ] **Step 1: Write the failing test**

Append to `scripts/test_multirepo.py`, above `if __name__ == "__main__":`:

```python
class RecordTest(unittest.TestCase):
    def test_the_map_names_the_new_scripts_and_workflows(self):
        mapping = read("docs/codebase-map.md")
        for name in ("check_contract_version.py", "check_contract_pin.py", "contract-check.yml", "contract-publish.yml"):
            self.assertIn(name, mapping, name)

    def test_the_plan_is_recorded(self):
        changes = read("docs/design/2026-11-19-aidlc-6-change-list.md")
        self.assertIn("Plan 20", changes)
        self.assertIn("Plan 21", changes)
        self.assertTrue((ROOT / "docs/verification/2026-11-20-plan-21.md").is_file())
```

- [ ] **Step 2: Run it to see it fail.** Run: `python3 -m unittest scripts.test_multirepo.RecordTest -v`. Expected: FAIL in both.

- [ ] **Step 3: Update the map and the change list, and write the record**

In `docs/codebase-map.md`, replace:

```markdown
`check_plan.py` (the plan check) and
`run_slices.py`
```

with:

```markdown
`check_plan.py` (the plan check),
`check_contract_version.py` (a provider's contract check, which `contract-check.yml` runs with oasdiff;
`contract-publish.yml` tags each new version), `check_contract_pin.py` (a consumer's vendored contracts) and
`run_slices.py`; `starter/workspace/scripts/story_status.py` derives each part's status, merge state and drift
```

In `docs/design/2026-11-19-aidlc-6-change-list.md`, replace `ADRs 0019–0021 proposed. Gate changes` with:

```markdown
ADRs 0019–0021 proposed. Phase 2a is planned in Plan 21
(`docs/plans/2026-11-20-plan-21-multirepo-foundations.md`); ADR 0022 proposed. Gate changes
```

Create `docs/verification/2026-11-20-plan-21.md` with these sections (the Plan 20 record is the model):
- **What changed:** the commit list (`git log --oneline main..HEAD`).
- **Evidence:** the outputs of `python3 scripts/validate.py`, `python3 -m unittest discover -s scripts -p 'test_*.py'`
  (the test count) and `claude plugin validate .`, each indented by four spaces.
- **Live checks:** Task 3, Step 5 (`gh pr list` fields); Task 7, Step 1 (oasdiff's release, checksum and flags).
- **Not verified here:**
  - the starter workflows on a real GitHub repository (`contract-check`, `contract-publish`, the `contract-pin`
    job), which need a public repository or a paid plan for required checks;
  - the oasdiff binary itself: the tests use a fake, and its exit codes come from its documentation and source;
  - a tag ruleset on `api-v*`;
  - the drift check and the merge state on a real multi-repository workspace (the shipment-tracking demo is parked
    by D4).
- **For the owner:** accept or amend ADR 0022, and decide the items under "Needs the owner's decision" in the plan.

- [ ] **Step 4: Run everything**

```bash
python3 scripts/validate.py
python3 -m unittest discover -s scripts -p 'test_*.py'
claude plugin validate .
```

Expected: the validator reports 0 problems; 629 tests pass; the plugin validates (only the known warning about the
root `CLAUDE.md`). Paste the outputs into the record.

- [ ] **Step 5: Commit**

```bash
git add docs/codebase-map.md docs/design/2026-11-19-aidlc-6-change-list.md docs/verification/2026-11-20-plan-21.md scripts/test_multirepo.py
git commit -m "docs(verification): Plan 21 record; the map names the contract scripts and workflows" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Out of scope (phase 2b)

- **F7:** a drift and integration workflow in the home repository that posts a required `story-gate` status on each
  child pull request, through a GitHub App. Today the drift check runs locally in `story_status.py` (Task 2), and
  nothing blocks a child's merge across repositories.
- **F8:** the integration check before the last part merges, against per-pull-request images pinned by digest in the
  home repository's compose file. `aidlc-release` keeps its integration check before any flag goes on.
- **F10:** GitHub App tokens per role (writer, reader, gate), each minted with explicit `repositories` and
  permissions.
- Also not here: F15 and decision D7 (the coordinator and scoped lanes, phase 5), G1–G6 (automatic change requests,
  phase 4), the shipment-tracking demo fixes I1–I4 (parked by D4), and Pact (a documented next step only).

## Self-review notes

- Spec coverage (change list section F, phase 2a):

  | Item | Where |
  |---|---|
  | F1 code that ships together goes in one repository | ADR 0022 (Task 1); `aidlc-onboard` step 0, `aidlc-design` new system, `aidlc-start` step 6 (Task 10) |
  | F2 each fact has one owner | ADR 0022; `stories/README.md` table (Task 8); `aidlc-design` Produces (Task 9); `WORKSPACE.md` and its template (Task 4) |
  | F3 ADRs by scope, `<KEY>-adr-<n>` | `adr.md`, `new-system.md`, `stories/README.md` (Task 8); `aidlc-design` step 5 and Produces (Task 9) |
  | F4 pins by version and home commit; frozen paths | `story_status.py` (Task 2); story index and bundle templates, coordination plan (Task 8); `aidlc-plan` step 7 (Task 9) |
  | F5 the read-only criteria copy | `criteria.md` template (Task 8); `aidlc-plan` step 8, verify, review, build, compliance (Task 9); the copy check in `story_status.py` (Task 2) |
  | F6 part status from real merge state | `story_status.py` (Task 3); story-index note (Task 8); `aidlc-release` step 1 (Task 10) |
  | The local drift check | `story_status.py` (Tasks 2 and 3: version, home commit, criteria copy, merge state) |
  | F9 the OpenAPI package (D5) with oasdiff (D9) | `check_contract_version.py` (Task 5); `check_contract_pin.py` (Task 6); workflows, CI job, AGENTS.md (Task 7); `designing-apis`, design's amendment mode (Task 11); onboard step 5 (Task 10) |
  | F11 Decision 2 across repositories | `aidlc-design` and `aidlc-plan` Gates (Task 10) |
  | F13 permalinks at the pinned commit | story-index template (Task 8); `aidlc-start` step 7, `aidlc-specify` step 7 (Task 10) |
  | F14 story repo hygiene | `--write-gitignore`, workspace `CODEOWNERS`, the runtime owner (Task 4); onboard step 0 (Task 10) |

- Every task was applied in order to a clean clone of `2ce7deb` while this plan was written, with the validator and
  the full suite run after each task: 550, 564, 572, 580, 593, 602, 612, 617, 620, 625, 627 and 629 tests, each run
  OK with 0 validator problems. The code and test blocks above are the ones that ran.
- No existing assertion changes. Each test that pins a sentence in a touched file was read first: `test_routes.py`
  (the part-index rows, PINS, merged row, "pointer", the workspace write rule), `test_handoffs.py` (fences,
  placeholders, identical copies, reviewer blocks), `test_gates_hold.py` (Gates, onboard, CI wiring),
  `test_greenfield.py` (new system), `test_loads.py` (loads), `test_story_status.py` (every behaviour of the status
  script), `test_check_plan.py` (the part's problem list), `test_one_plugin.py` (start's step numbers, the version).

## Needs the owner's decision

Checked: no task changes an existing assertion. These parts of the change list are deliberately not done, because
doing them would change one:

1. **F6 says "Remove the hand-marked 'merged' rows."** This plan keeps the row and checks it against the real merge
   state instead. Removing it conflicts with:
   - `scripts/test_routes.py:294`: `self.assertIn("marks the \`merged\` row done in its final commit", skill("aidlc-review"))`;
   - `scripts/test_routes.py:164`: the part index's rows include `` `merged` `` (`aidlc-plan`);
   - `scripts/test_story_status.py:100-112` and `:124`: release readiness and `| 1 | shipments-api | merged |` come
     from that row.

   Options: (a) keep the row as a checked, human-marked record (this plan); (b) drop the row in a later plan, with
   those assertions changed by the owner, and make the merge state alone decide release readiness; (c) let
   `story_status.py --write` print the merge state into `status.md` only, and stop asking people to mark the row.
2. **F6 says "`--check-release` no longer reads local clones."** It still requires each clone on its default branch.
   That is pinned by `scripts/test_story_status.py:242-260` (`test_check_release_needs_each_repository_on_its_default_branch`:
   exit 1 and "web-portal: on branch feat/SHIP-1-2-r2, not its default branch main") and `:262-271` ("not a git
   repository"). With Task 3, the merge state no longer depends on the checked-out branch, so the branch rule could
   be relaxed. Options: (a) keep it (this plan); (b) relax it in a later plan with the owner's change to those
   assertions.
3. **The 6.0.0 version.** The change list says the major version rises when phases 1 and 2 land.
   `scripts/test_one_plugin.py:100` pins `"5.0.0"`. Phase 2b is still to come. Options: raise it after 2b, or now.
