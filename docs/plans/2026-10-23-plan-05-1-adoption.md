# Plan 5.1: Adopting an existing repository. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An existing repository can adopt aidlc without a rewrite and without "red forever":
- a read-only survey says what is there;
- a reviewed patch imports the other tools' rule files;
- a baseline records today's debt, with an owner and a date for each item;
- from then on the trusted CI only lets that debt shrink (the ratchet).

**Architecture.** The flow, in five steps:

```text
existing repo
  1. aidlc adopt            read-only survey → adoption report (stack, commands, agent config, CI, secrets)
  2. aidlc init-repo        scaffold (never overwrites; already built)
  3. aidlc adopt --import   a patch: CLAUDE.md, Copilot and Cursor rule files → AGENTS.md and .aidlc/rules/
     git apply <patch>      the person reads and applies it
  4. .aidlc/baseline.yaml   today's debt: report-only steps and temporary skips, each with owner and date
  5. adoption pull request  normal review; then the owner switches on the required checks
     every later pull request: the baseline only shrinks (CI judge step "baseline")
```

The pieces:
- **`cli/aidlc/baseline.py`** parses `.aidlc/baseline.yaml`. Trusted CI reads it from the base branch, like `test/allowed-skips.txt`. Two uses:
  - the command steps it lists run report-only (status `reported`, not FAIL);
  - the skips step accepts the test names it lists.
- **The ratchet.** A new CI judge step, `baseline`, fails a change whose baseline grows, or that holds an entry past its review date.
- **`aidlc adopt`** (`cli/aidlc/adopt.py`, with stack hints as data in `core/context/stack-hints.yaml`) writes the report. `--import` writes the patch.
- **`legacy_paths`** in `.aidlc/config.yaml`, with skill text: pin today's behaviour with a test before changing those files.
- **The `aidlc-adopt` skill** (manual) walks a person through the steps.

**Tech Stack:** Python 3.12 (stdlib, PyYAML), git, the existing check and CI machinery. No new dependency.

**Spec:**
- the design discussion of 2026-10-23, agreed by the owner:
  - the survey, the import patch, the baseline and ratchet, the two-speed rule, one manual skill;
  - **secrets are never baselined: they are fixed before adoption;**
  - **no new stack profiles:** existing repositories use `generic` with their own commands;
- guide 16.5 (roll out against a baseline), 15.7 (pin today's behaviour), 2.8 (Procedure A), chapter 4;
- ADR 0002 (trusted CI), ADR 0005 (skills plugin), ADR 0006 (multi-tool foundation: other tools' configuration is unmanaged until imported).

## Facts this plan relies on (read in the code on 2026-10-23)

- **`init_repo`** (`cli/aidlc/repo.py`) never overwrites: `_write` reports "skipped (exists)".
- **The trusted CI** (`ci.run_ci`) needs `.aidlc/config.yaml` on the base branch, so the adoption pull request itself cannot pass it. The owner reviews it normally, and adds the required checks after it merges. New repositories follow the same order today.
- **Steering files.** `onecheck.STEERING = (EXCEPTIONS, ALLOWED_SKIPS)` are files CI reads from the base before any of the change's code runs (`ci._steering`, `ctx.steering`). `_allowed_skips` reads `ctx.steering` in CI and the working copy locally.
- **Step lists.**
  - `onecheck.BUILTINS` is pinned exactly by `tests/unit/test_onecheck_skips.py::test_builtins_order`, so the local check gains no step.
  - `ci.JUDGE_STEPS` must end with `config-policy`, and `ci.AFTER_STEPS` is pinned to `["skips", "protected-rerun"]` (`tests/unit/test_conftest_check.py`).
- **Statuses** are `OK, FAIL, SKIPPED, NA`. `CheckResult.failures` counts only `FAIL`.
- **Folder rules** are `.aidlc/rules/*.md` with front matter `paths:`, a non-empty list of globs (`ClaudeCodeAdapter.render_folder_rules`).
- **Agent configuration** is recognised by `checks.conftest_check._is_agent_config(_fold(path))`, from every tool's descriptor. `CLAUDE.md` is not in that list, because `render_rules` generates it.
- **Secret-shaped text** is `hooks().guard.BLOCK_SECRET_RE` (`aidlc.hookbridge.hooks`).
- **Test reports** are already read as JSON, TRX and JUnit XML (`checks/test_reports.py`), so a stack needs no new parser.

## Global Constraints

- **Dependencies.** No new dependency. The hooks are untouched.
- **Tests.**
  - Never change an existing test assertion. `BUILTINS`, the end of `JUDGE_STEPS` and `AFTER_STEPS` stay as pinned.
  - `make test` stays model-free.
- **Fail closed.**
  - A malformed baseline is a FAIL, never "no baseline".
  - `aidlc adopt` exits 1 when it finds secret-shaped text, and 2 on usage errors.
  - `--import` refuses to run before `init-repo`, and never writes over an existing file.
- **Never write a person's file.**
  - `aidlc adopt` writes nothing. `--import` prints a patch; the person applies it.
  - The baseline is written by the person and reviewed by code owners.
- **What may be baselined:**
  - command steps other than `test`, `build`, `install` and `restore` may be report-only;
  - tests may be temporarily skipped;
  - secrets never (owner decision);
  - the judge steps (scope, protected tests, secrets, config-policy) never.
- **Commits, pushes and approvals** follow the established rules: the noreply identity, explicit paths, a pre-push scan, and the user's go-ahead for each push and merge.
- **Run before every commit:**
  - `make test`;
  - `make policy-test` with `AIDLC_TOOLS_DIR`;
  - `bin/aidlc trace --check`;
  - `bin/aidlc check context-drift .`;
  - `bin/aidlc policy validate`;
  - `bin/aidlc plugin build --check`.

  Commit only after they pass.

## Review Focus

1. **A pull request that adds a baseline entry for a step the base already runs**, or a new skip. Trusted CI FAILs it. Pinned by Task 2 `test_a_new_entry_fails_the_ratchet`.
2. **A baseline entry past its review date.** The ratchet FAILs every pull request until it is fixed or its owner moves the date. Pinned by Task 2 `test_an_expired_entry_fails`; report-only stops applying, by Task 1 `test_an_expired_report_only_entry_fails_again`.
3. **A malformed or symlinked baseline**, locally and in CI. FAIL, never a silent "no baseline". Pinned by Task 1 `test_a_malformed_baseline_fails_closed` and Task 2 `test_a_linked_head_baseline_fails`.
4. **A report-only entry for `test` or `build`.** Refused at parse time. Pinned by Task 1 `test_test_and_build_can_never_be_report_only`.
5. **The import patch on a repository whose `.aidlc/rules/<name>.md` already exists**, or with hand-written `CLAUDE.md` content. The patch never overwrites a file, and it applies cleanly with `git apply`. Pinned by Task 5 `test_the_patch_applies_and_never_overwrites`.

---

### Task 1: The baseline: report-only steps and temporary skips

**Files:**
- Create: `cli/aidlc/baseline.py`, `tests/unit/test_baseline.py`
- Modify: `cli/aidlc/checks/onecheck.py` (`REPORTED`, `STEERING`, `_baseline`, `report_only`, `run_check`, `step_skips`), `cli/aidlc/ci.py` (`_run_phases` wraps command steps)

**Interfaces:**
- `baseline.BASELINE = ".aidlc/baseline.yaml"`.
- `baseline.Entry(kind, key, owner, review_by, reason)`.
- `baseline.parse(text, label) -> list[Entry]` (raises `BaselineError`).
- `baseline.active(entries, kind, today=None) -> dict[str, Entry]`.
- `onecheck.REPORTED = "reported"`.
- `onecheck.report_only(ctx, result) -> StepResult`.
- `onecheck._baseline(ctx) -> list[Entry]`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_baseline.py
import unittest
from datetime import date, timedelta

from aidlc import baseline
from aidlc.baseline import BaselineError, active, parse
from aidlc.checks import onecheck
from aidlc.checks.onecheck import FAIL, OK, REPORTED, StepResult, local_context, report_only, run_check
from aidlc.repo import load_config
from tests.unit.test_guard import GuardEnv
from tests.unit.test_onecheck import installed, py
from tests.unit.test_onecheck_skips import REPORT, write_report

FUTURE = (date.today() + timedelta(days=30)).isoformat()
PAST = (date.today() - timedelta(days=1)).isoformat()


def entry(kind="report_only", key="lint", when=FUTURE):
    field = "step" if kind == "report_only" else "test"
    return f"{kind}:\n  - {{{field}: {key!r}, owner: '@team', review_by: '{when}', reason: 'existing debt'}}\n"


class ParseTest(unittest.TestCase):
    def test_empty_means_no_entries(self):
        self.assertEqual(parse(""), [])

    def test_both_kinds(self):
        entries = parse(entry() + entry("skips", "pkg.A skip"))
        self.assertEqual({(e.kind, e.key) for e in entries}, {("report_only", "lint"), ("skips", "pkg.A skip")})

    def test_test_and_build_can_never_be_report_only(self):
        for step in ("test", "build", "install", "restore"):
            with self.subTest(step=step), self.assertRaises(BaselineError):
                parse(entry(key=step))

    def test_a_malformed_baseline_fails_closed(self):
        for text in ("[1, 2]", "report_only: x\n", "secrets: []\n", "report_only:\n  - {step: lint}\n",
                     entry().replace("'@team'", "''"), entry(when="soon"), entry() + entry()[len("report_only:\n"):]):
            with self.subTest(text=text), self.assertRaises(BaselineError):
                parse(text)

    def test_active_drops_expired_entries(self):
        entries = parse(entry(when=PAST))
        self.assertEqual(active(entries, "report_only"), {})


class ReportOnlyTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("raise SystemExit(1)")}, ["lint"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def lint(self, text=None):
        if text is not None:
            (self.root / baseline.BASELINE).write_text(text, encoding="utf-8")
        ctx = local_context(self.root, load_config(self.root))
        return run_check(ctx, builtins=[]).steps[0]

    def test_a_failing_step_fails_without_a_baseline(self):
        self.assertEqual(self.lint().status, FAIL)

    def test_a_baselined_step_is_reported_not_failed(self):
        step = self.lint(entry())
        self.assertEqual(step.status, REPORTED)
        self.assertIn("report-only until", step.detail)

    def test_an_expired_report_only_entry_fails_again(self):
        self.assertEqual(self.lint(entry(when=PAST)).status, FAIL)

    def test_a_passing_step_stays_ok(self):
        ctx = local_context(self.root, load_config(self.root))
        self.assertEqual(report_only(ctx, StepResult("lint", OK, "")).status, OK)

    def test_ci_reads_the_base_baseline_not_the_change(self):
        (self.root / baseline.BASELINE).write_text(entry(), encoding="utf-8")
        ctx = local_context(self.root, load_config(self.root))
        ctx.steering = {}                                  # the base has no baseline
        self.assertEqual(report_only(ctx, StepResult("lint", FAIL, "x")).status, FAIL)

    def test_a_malformed_baseline_fails_the_step(self):
        self.assertEqual(self.lint("report_only: nope\n").status, FAIL)


class BaselineSkipsTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        cmd = write_report("<testsuite><testcase classname='pkg.A' name='ok'/>"
                           "<testcase classname='pkg.A' name='skip'><skipped/></testcase></testsuite>")
        self.repo, self.root = installed({"test": cmd}, ["test"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def skips(self):
        ctx = local_context(self.root, load_config(self.root))
        ctx.config.test_reports = [REPORT]
        return run_check(ctx, builtins=[("skips", onecheck.step_skips)]).steps[-1]

    def test_a_baselined_skip_is_accepted_until_its_date(self):
        self.assertEqual(self.skips().status, FAIL)
        (self.root / baseline.BASELINE).write_text(entry("skips", "pkg.A skip"), encoding="utf-8")
        self.assertEqual(self.skips().status, OK)
        (self.root / baseline.BASELINE).write_text(entry("skips", "pkg.A skip", PAST), encoding="utf-8")
        self.assertEqual(self.skips().status, FAIL)

    def test_reported_does_not_count_as_a_failure(self):
        result = onecheck.CheckResult([StepResult("lint", REPORTED, "")])
        self.assertTrue(result.passed)
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_baseline -v`. Expected: `ImportError` (no `aidlc.baseline`).
- [ ] **Step 3: Implement.**

```python
# cli/aidlc/baseline.py
"""The adoption baseline (ADR 0007): `.aidlc/baseline.yaml` lists the debt a repository accepted when it
adopted aidlc. Each entry has an owner, a review date and a reason. Two kinds:

    report_only:                         # a command step that runs but does not fail the check yet
      - {step: lint, owner: "@team", review_by: "2027-01-31", reason: "1,240 existing lint errors"}
    skips:                               # a test that may be skipped until its date
      - {test: "pkg.A slow", owner: "@team", review_by: "2027-01-31", reason: "needs the carrier sandbox"}

Trusted CI reads the base branch's copy, so a change cannot widen its own allowance, and the `baseline`
judge step lets the file only shrink. `test`, `build`, `install` and `restore` can never be report-only,
and secrets are never baselined: they are fixed before adoption."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import yaml

BASELINE = ".aidlc/baseline.yaml"
NEVER_REPORT_ONLY = frozenset({"test", "build", "install", "restore"})
_KEY = {"report_only": "step", "skips": "test"}


class BaselineError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    kind: str            # "report_only" or "skips"
    key: str             # the step name, or the test name as the test report gives it
    owner: str
    review_by: date
    reason: str


def _date(value: object, label: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise BaselineError(f"{label}: review_by must be a date such as 2027-01-31, got {value!r}")


def parse(text: str, label: str = BASELINE) -> list[Entry]:
    if not text.strip():
        return []
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BaselineError(f"{label}: not valid YAML ({type(exc).__name__})") from None
    if not isinstance(data, dict) or set(data) - set(_KEY):
        raise BaselineError(f"{label}: only the lists 'report_only' and 'skips' are allowed")
    out: list[Entry] = []
    for kind, field in _KEY.items():
        items = data.get(kind) or []
        if not isinstance(items, list):
            raise BaselineError(f"{label}: '{kind}' must be a list")
        for item in items:
            if not isinstance(item, dict) or set(item) != {field, "owner", "review_by", "reason"}:
                raise BaselineError(f"{label}: every {kind} entry has exactly {field}, owner, review_by and reason")
            key, owner, reason = item[field], item["owner"], item["reason"]
            if not all(isinstance(v, str) and v.strip() for v in (key, owner, reason)):
                raise BaselineError(f"{label}: {kind} entries need a non-empty {field}, owner and reason")
            if kind == "report_only" and key in NEVER_REPORT_ONLY:
                raise BaselineError(f"{label}: '{key}' can never be report-only; a failing {key} is a broken repository")
            out.append(Entry(kind, key.strip(), owner.strip(), _date(item["review_by"], label), reason.strip()))
    seen: set[tuple[str, str]] = set()
    for e in out:
        if (e.kind, e.key) in seen:
            raise BaselineError(f"{label}: {e.kind} '{e.key}' is listed twice")
        seen.add((e.kind, e.key))
    return out


def active(entries: list[Entry], kind: str, today: date | None = None) -> dict[str, Entry]:
    """The entries of one kind still before their review date."""
    today = today or date.today()
    return {e.key: e for e in entries if e.kind == kind and e.review_by >= today}
```

In `cli/aidlc/checks/onecheck.py`:

1. **Import:** `from ..baseline import BASELINE, active, parse as parse_baseline`.
2. **Status:** set `OK, FAIL, SKIPPED, NA = …` unchanged, then add `REPORTED = "reported"   # failed, but the baseline accepts it for now: not a failure`.
3. **Steering:** `STEERING = (EXCEPTIONS, ALLOWED_SKIPS, BASELINE)`.
4. **The helpers:**

```python
def _baseline(ctx: CheckContext) -> list:
    """The accepted debt. CI: the base branch's copy (ctx.steering); locally: the working copy."""
    if ctx.steering is not None:
        return parse_baseline(ctx.steering.get(BASELINE, ""), f"base {BASELINE}")
    path = ctx.repo / BASELINE
    if path.is_symlink():
        raise ValueError(f"{BASELINE} is a symlink; the check does not follow it")
    return parse_baseline(path.read_text(encoding="utf-8") if path.is_file() else "")


def report_only(ctx: CheckContext, result: StepResult) -> StepResult:
    """A failing command step the baseline lists, before its review date, is reported, not failed."""
    if result.status != FAIL:
        return result
    entry = active(_baseline(ctx), "report_only").get(result.name)
    if entry is None:
        return result
    result.status = REPORTED
    result.detail = (f"{result.detail} " if result.detail else "") + \
        f"[report-only until {entry.review_by}, owner {entry.owner}: {entry.reason}]"
    return result
```

5. **`run_check`:** `_guarded(name, lambda n=name: report_only(ctx, run_command(ctx, n)))`.
6. **`step_skips`:** `allowed = _allowed_skips(ctx) | set(active(_baseline(ctx), "skips"))`.

In `cli/aidlc/ci.py` `_run_phases`, the command loop becomes `guarded(name, lambda n=name: report_only(ctx, run_command(ctx, n)))`. Import `report_only` with the other `onecheck` names.

Where step results are printed, show `reported` as it is. The summary still counts failures only.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, then `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_onecheck_skips tests.unit.test_onecheck tests.unit.test_ci -v` and `make test`. Expected: everything passes. Any existing test that asserts `STEERING` or a printed status line is a finding: stop and report, and do not change it.
- [ ] **Step 5: Commit.** Commit with `feat(checks): the adoption baseline: report-only command steps and temporary skips, read from the base in CI`.

### Task 2: The ratchet: a CI judge step that lets the baseline only shrink

**Files:**
- Modify: `cli/aidlc/ci.py` (`step_baseline`, plus `JUDGE_STEPS` before `config-policy`)
- Test: `tests/unit/test_baseline_ratchet.py`

**Interfaces:** `ci.step_baseline(ctx) -> StepResult`. It consumes `baseline.parse` and `active` (Task 1) and `ctx.steering`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_baseline_ratchet.py
import os
import unittest
from datetime import date, timedelta

from aidlc import ci
from aidlc.baseline import BASELINE
from aidlc.checks.onecheck import FAIL, OK, local_context
from aidlc.repo import load_config
from tests.unit.test_baseline import FUTURE, PAST, entry
from tests.unit.test_guard import GuardEnv
from tests.unit.test_onecheck import installed, py


class RatchetTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("pass"), "format": py("pass")}, ["lint"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def judge(self, base_text, head_text):
        if head_text is not None:
            (self.root / BASELINE).write_text(head_text, encoding="utf-8")
        ctx = local_context(self.root, load_config(self.root))
        ctx.steering = {} if base_text is None else {BASELINE: base_text}
        return ci.step_baseline(ctx)

    def test_runs_in_ci_before_config_policy(self):
        names = [n for n, _ in ci.JUDGE_STEPS]
        self.assertEqual(names[-2:], ["baseline", "config-policy"])

    def test_no_baseline_anywhere_passes(self):
        self.assertEqual(self.judge(None, None).status, OK)

    def test_shrinking_passes(self):
        both = entry() + entry("skips", "pkg.A skip")
        step = self.judge(both, entry())
        self.assertEqual(step.status, OK)
        self.assertIn("1 paid off", step.detail)

    def test_a_new_entry_fails_the_ratchet(self):
        for head in (entry(), entry("skips", "pkg.A skip")):
            with self.subTest(head=head):
                step = self.judge("", head)
                self.assertEqual(step.status, FAIL)
                self.assertIn("may only shrink", step.detail)

    def test_a_new_step_may_start_report_only(self):
        self.assertEqual(self.judge("", entry(key="format")).status, OK)   # format is not in the base's check_steps

    def test_an_expired_entry_fails(self):
        step = self.judge(entry(when=PAST), entry(when=PAST))
        self.assertEqual(step.status, FAIL)
        self.assertIn("review date", step.detail)

    def test_moving_a_date_is_a_reviewed_decision_not_growth(self):
        later = (date.today() + timedelta(days=90)).isoformat()
        self.assertEqual(self.judge(entry(), entry(when=later)).status, OK)

    def test_a_linked_head_baseline_fails(self):
        target = self.root / "elsewhere.yaml"
        target.write_text(entry(), encoding="utf-8")
        os.symlink(target, self.root / BASELINE)
        self.assertEqual(self.judge(entry(), None).status, FAIL)

    def test_a_malformed_head_baseline_fails(self):
        self.assertEqual(self.judge("", "report_only: nope\n").status, FAIL)
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_baseline_ratchet -v`. Expected: `AttributeError` (no `step_baseline`).
- [ ] **Step 3: Implement.** In `cli/aidlc/ci.py`, import `from .baseline import BASELINE, BaselineError, parse as parse_baseline` and add:

```python
def step_baseline(ctx: CheckContext) -> StepResult:
    """The ratchet (ADR 0007): the change's .aidlc/baseline.yaml may only shrink. It is compared with the
    base's copy, read before any of the change's code runs. A skip, or a report-only step the base
    already runs, that the base does not list FAILs; so does any entry past its review date. A step new
    in this change may start report-only. Moving an owner, reason or date is a decision the code owners
    review, not growth."""
    try:
        base = parse_baseline((ctx.steering or {}).get(BASELINE, ""), f"base {BASELINE}")
        path = ctx.repo / BASELINE
        if path.is_symlink():
            return StepResult("baseline", FAIL, f"{BASELINE} is a symlink; the judge does not follow it")
        head = parse_baseline(path.read_text(encoding="utf-8") if path.is_file() else "")
    except (BaselineError, OSError, UnicodeDecodeError) as exc:
        return StepResult("baseline", FAIL, str(exc))
    known = {(e.kind, e.key) for e in base}
    runs = set(ctx.config.check_steps)                # the base's configuration judges the change
    today = date.today()
    problems = []
    for e in head:
        new_step = e.kind == "report_only" and e.key not in runs
        if (e.kind, e.key) not in known and not new_step:
            problems.append(f"{e.kind} '{e.key}' is new: the baseline may only shrink")
        if e.review_by < today:
            problems.append(f"{e.kind} '{e.key}' passed its review date {e.review_by}: fix it, or its owner "
                            "moves the date in a reviewed change")
    if problems:
        return StepResult("baseline", FAIL, "; ".join(problems[:5]))
    paid = len(known - {(e.kind, e.key) for e in head})
    return StepResult("baseline", OK, f"{len(head)} entries" + (f", {paid} paid off" if paid else ""))
```

Put `("baseline", step_baseline),` in `JUDGE_STEPS` just before `("config-policy", step_config_policy)`. Add `from datetime import date` if the module lacks it.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_conftest_check tests.unit.test_ci -v` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(ci): the baseline ratchet: a judge step that lets accepted debt only shrink and fails expired entries`.

### Task 3: Two-speed rule: `legacy_paths`

**Files:**
- Modify:
  - `cli/aidlc/repo.py` (`RepoConfig.legacy_paths`, validated in `load_config`);
  - `core/skills/aidlc-plan/SKILL.md`, `core/skills/aidlc-build-slice/SKILL.md`;
  - `tests/unit/test_skills_format.py` (one new test);
  - regenerate `plugins/aidlc/`.
- Test: `tests/unit/test_legacy_paths.py`

**Interfaces:** `RepoConfig.legacy_paths: list[str]` (default `[]`).

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_legacy_paths.py
import unittest
from datetime import date

import yaml

from aidlc.repo import CONFIG, init_repo, load_config
from tests.helpers import TempRepo


class LegacyPathsTest(unittest.TestCase):
    def config(self, value):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            data = yaml.safe_load((root / CONFIG).read_text(encoding="utf-8"))
            data["legacy_paths"] = value
            (root / CONFIG).write_text(yaml.safe_dump(data), encoding="utf-8")
            return load_config(root)

    def test_default_is_none(self):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            self.assertEqual(load_config(root).legacy_paths, [])

    def test_globs_are_kept(self):
        self.assertEqual(self.config(["src/billing/**", "lib/old_*.py"]).legacy_paths,
                         ["src/billing/**", "lib/old_*.py"])

    def test_bad_values_fail_closed(self):
        for value in ("src/**", [1], ["/etc/x"], ["../up/**"], [""]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.config(value)
```

Append to `tests/unit/test_skills_format.py`:

```python
    def test_legacy_paths_need_a_pinning_test_first(self):
        rule = ("Files matching `legacy_paths` in `.aidlc/config.yaml` have no tests that pin their behaviour: "
                "change one only after a characterisation test records what it does today.")
        for name in ("aidlc-plan", "aidlc-build-slice"):
            with self.subTest(skill=name):
                self.assertIn(rule, (SKILLS / name / "SKILL.md").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_legacy_paths tests.unit.test_skills_format -v`. Expected: `AttributeError` (no `legacy_paths`), and the skill test fails.
- [ ] **Step 3: Implement.**
  - **`RepoConfig`:** add `legacy_paths: list[str] = field(default_factory=list)`.
  - **`load_config`:** read `data.get("legacy_paths", [])`. It must be a list of non-empty relative strings, with no leading `/` and no `..` part. Otherwise raise `ValueError(f"{CONFIG}: 'legacy_paths' must be a list of relative globs, got {value!r}")`.
  - **Both skills:** add the sentence from the test word for word. Plan: as a bullet in step 3's constraints. Build-slice: as a "Stop if" bullet that starts with the sentence.
  - Run `bin/aidlc plugin build`.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, `bin/aidlc plugin build --check` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(config): legacy_paths, and the plan and build-slice skills pin today's behaviour before changing them`.

### Task 4: `aidlc adopt`, the read-only survey

**Files:**
- Create:
  - `cli/aidlc/adopt.py`;
  - `cli/aidlc/commands/adopt_cmd.py` (with its import line in `cli/aidlc/commands/__init__.py`);
  - `core/context/stack-hints.yaml`;
  - `tests/unit/test_adopt.py`.

**Interfaces:**
- `adopt.survey(repo) -> Survey`, with the fields:
  - `stacks: list[dict]`;
  - `agent_config: list[tuple[str, str, str]]` (path, tool, action: `import`, `managed` or `decide`);
  - `workflows: list[str]`;
  - `secrets: list[str]`;
  - `installed: bool`.
- `adopt.report(survey) -> str` (Markdown).
- The command `aidlc adopt [path]` exits:
  - 0: the report;
  - 1: secret-shaped text found;
  - 2: not a repository root.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_adopt.py
import unittest

from aidlc import adopt
from tests.helpers import TempRepo, run_cli

KEY = "sk-ant-" + "a" * 40          # secret-shaped, assembled so this file holds none


class SurveyTest(unittest.TestCase):
    def test_stack_commands_and_agent_config(self):
        files = {"pyproject.toml": "[project]\nname='x'\n", "CLAUDE.md": "Use pytest.\n",
                 ".cursor/rules/api.mdc": "---\nglobs: src/api/**\n---\nKeep handlers thin.\n",
                 ".github/workflows/ci.yml": "on: push\n", "src/app.py": "print(1)\n"}
        with TempRepo(files) as root:
            s = adopt.survey(root)
            self.assertEqual([st["name"] for st in s.stacks], ["python"])
            self.assertIn(("CLAUDE.md", "claude-code", "import"), s.agent_config)
            self.assertIn((".cursor/rules/api.mdc", "cursor", "import"), s.agent_config)
            self.assertEqual(s.workflows, [".github/workflows/ci.yml"])
            self.assertEqual((s.secrets, s.installed), ([], False))
            text = adopt.report(s)
            for needle in ("python", "--junitxml", "CLAUDE.md", "aidlc init-repo", "aidlc adopt --import"):
                self.assertIn(needle, text)

    def test_hand_written_skills_need_a_decision(self):
        with TempRepo({".claude/skills/x/SKILL.md": "---\nname: x\n---\n", "README.md": "x\n"}) as root:
            self.assertIn((".claude/skills/x/SKILL.md", "claude-code", "decide"), adopt.survey(root).agent_config)

    def test_secrets_stop_the_adoption(self):
        with TempRepo({"config.py": f"KEY = '{KEY}'\n"}) as root:
            code, out, _ = run_cli("adopt", str(root))
            self.assertEqual(code, 1)
            self.assertIn("config.py", out)
            self.assertNotIn(KEY, out)                 # names the file, never the text

    def test_the_survey_writes_nothing(self):
        with TempRepo({"package.json": "{}\n", "CLAUDE.md": "x\n"}) as root:
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if ".git" not in p.parts)
            code, _, _ = run_cli("adopt", str(root))
            after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if ".git" not in p.parts)
            self.assertEqual((code, before), (0, after))

    def test_not_a_repository_root_is_a_usage_error(self):
        with TempRepo({"sub/x.py": "x\n"}) as root:
            code, _, _ = run_cli("adopt", str(root / "sub"))
            self.assertEqual(code, 2)
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_adopt -v`. Expected: `ImportError`.
- [ ] **Step 3: Implement.**

`core/context/stack-hints.yaml` (data; the survey suggests, the person decides):

```yaml
# Stack hints for `aidlc adopt`: how to recognise a stack, and suggested commands for a repository that
# uses the `generic` profile. Suggestions only; the repository's .aidlc/config.yaml decides.
- {name: node, files: [package.json], profile: node}
- {name: dotnet, files: ["*.csproj", "*.sln", global.json], profile: dotnet}
- name: python
  files: [pyproject.toml, setup.py, setup.cfg, requirements.txt]
  profile: generic
  commands: {test: "python3 -m pytest -q --junitxml=.check/junit.xml"}
  check_steps: [test]
  test_reports: [.check/junit.xml]
- name: maven
  files: [pom.xml]
  profile: generic
  commands: {test: "mvn -B -q verify"}
  check_steps: [test]
  test_reports: ["target/surefire-reports/*.xml"]
- name: gradle
  files: [build.gradle, build.gradle.kts]
  profile: generic
  commands: {test: "./gradlew test --console=plain"}
  check_steps: [test]
  test_reports: ["build/test-results/test/*.xml"]
- name: go
  files: [go.mod]
  profile: generic
  commands: {test: "gotestsum --junitfile .check/junit.xml ./..."}
  check_steps: [test]
  test_reports: [.check/junit.xml]
  note: "go test writes no JUnit report; gotestsum does (install it in the repository's toolchain)"
```

`cli/aidlc/adopt.py`:

```python
"""`aidlc adopt` (ADR 0007): a read-only survey of an existing repository, and (`--import`) a patch that
moves other tools' rule files into AGENTS.md and .aidlc/rules/. It writes nothing; the person reviews
and applies the patch. Secrets are never baselined: the survey stops the adoption until they are fixed."""
from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .adapters.base import _is_generated
from .adapters.capabilities import load_capabilities
from .checks.conftest_check import _fold, _is_agent_config
from .hookbridge import hooks
from .paths import framework_root
from .policy import load_yaml
from .repo import CONFIG

MAX_SCAN = 1_000_000
IMPORTABLE = ("CLAUDE.md", ".cursorrules", ".github/copilot-instructions.md")
IMPORTABLE_GLOBS = (".cursor/rules/*.mdc", ".github/instructions/*.instructions.md")


@dataclass
class Survey:
    repo: Path
    stacks: list[dict] = field(default_factory=list)
    agent_config: list[tuple[str, str, str]] = field(default_factory=list)
    workflows: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    installed: bool = False


def _tracked(repo: Path) -> list[str]:
    out = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "ls-files", "-z"], cwd=repo,
                         capture_output=True, text=True, check=True, timeout=60).stdout
    return [p for p in out.split("\0") if p]


def importable(rel: str) -> bool:
    return rel in IMPORTABLE or any(fnmatch.fnmatchcase(rel, g) for g in IMPORTABLE_GLOBS)


def _tool(rel: str) -> str:
    if rel == "CLAUDE.md":
        return "claude-code"
    folded, parts = _fold(rel), _fold(rel).split("/")
    for name, data in load_capabilities().items():
        config = data["agent_config"]
        if (any(p in {d.casefold() for d in config["dir_names"]} for p in parts)
                or parts[-1] in {f.casefold() for f in config["file_names"]}
                or folded.startswith(tuple(p.casefold() for p in config["prefixes"]))):
            return name
    return "aidlc"


def survey(repo: Path) -> Survey:
    s = Survey(repo=repo, installed=(repo / CONFIG).is_file())
    tracked = _tracked(repo)
    names = {PurePosixPath(p).name for p in tracked if "/" not in p}
    for hint in load_yaml(framework_root() / "core" / "context" / "stack-hints.yaml"):
        if any(fnmatch.filter(names, pattern) for pattern in hint["files"]):
            s.stacks.append(hint)
    secret = hooks().guard.BLOCK_SECRET_RE
    for rel in tracked:
        path = repo / rel
        if path.is_symlink() or not path.is_file():
            continue
        if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml")):
            s.workflows.append(rel)
        if rel == "CLAUDE.md" or _is_agent_config(_fold(rel)):
            text = path.read_text(encoding="utf-8", errors="replace") if path.stat().st_size <= MAX_SCAN else ""
            action = "managed" if _is_generated(text) else "import" if importable(rel) else "decide"
            s.agent_config.append((rel, _tool(rel), action))
        if path.stat().st_size <= MAX_SCAN:
            data = path.read_bytes()
            if b"\0" not in data and secret.search(data.decode("utf-8", errors="replace")):
                s.secrets.append(rel)
    return s


def report(s: Survey) -> str:
    lines = [f"# Adoption report: {s.repo.name}", ""]
    if s.secrets:
        lines += ["## Stop: secret-shaped text", "Fix these before adopting (rotate the credential, then remove it; "
                  "secrets are never baselined):", *[f"- `{p}`" for p in s.secrets], ""]
    lines += ["## Stack and suggested commands"]
    if not s.stacks:
        lines.append("- none recognised: use the `generic` profile and write the commands in `.aidlc/config.yaml`")
    for st in s.stacks:
        lines.append(f"- **{st['name']}** → profile `{st['profile']}`" +
                     (f"; commands {st['commands']}, reports {st.get('test_reports', [])}" if st.get("commands") else "") +
                     (f" ({st['note']})" if st.get("note") else ""))
    lines += ["", "## Agent configuration found"]
    labels = {"import": "imported by `aidlc adopt --import`", "managed": "generated by aidlc",
              "decide": "decide: keep it as a plugin, move it, or remove it (the CI judge fails unmanaged config)"}
    lines += [f"- `{p}` ({tool}): {labels[action]}" for p, tool, action in s.agent_config] or ["- none"]
    lines += ["", "## Existing CI", *([f"- `{w}` (stays; aidlc adds its own workflow)" for w in s.workflows] or ["- none"])]
    lines += ["", "## Next steps",
              "1. Fix any secret above." if s.secrets else "1. No secret-shaped text found.",
              "2. `aidlc init-repo . --profile <profile> …` (never overwrites)." if not s.installed else
              "2. aidlc is already initialised here.",
              "3. `aidlc adopt --import > adopt.patch`, read it, then `git apply adopt.patch`.",
              "4. `aidlc render --tool claude-code`, then write `.aidlc/baseline.yaml` for today's debt "
              "(docs/adoption/README.md).",
              "5. Open the adoption pull request; after it merges, switch on the required checks."]
    return "\n".join(lines) + "\n"
```

`cli/aidlc/commands/adopt_cmd.py`:

```python
"""aidlc adopt: survey an existing repository (read-only), or print the import patch (ADR 0007)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import adopt
from ..cli import command


def _run(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    if not (repo / ".git").exists():
        print(f"aidlc adopt: {repo} is not the root of a git repository", file=sys.stderr)
        return 2
    try:
        if args.import_patch:
            patch, problems = adopt.import_patch(repo)
            for problem in problems:
                print(f"aidlc adopt: {problem}", file=sys.stderr)
            sys.stdout.write(patch)
            return 0
        s = adopt.survey(repo)
    except adopt.AdoptError as exc:
        print(f"aidlc adopt: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(adopt.report(s))
    return 1 if s.secrets else 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("adopt", help="survey an existing repository, or print the import patch")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--import", dest="import_patch", action="store_true",
                        help="print a patch moving other tools' rule files into AGENTS.md and .aidlc/rules/")
    parser.set_defaults(func=_run)
```

Task 5 defines `AdoptError` and `import_patch`. Add `class AdoptError(Exception): pass` to `adopt.py` in this task, so the command imports cleanly.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(adopt): aidlc adopt, a read-only survey of an existing repository (stack, commands, agent config, CI, secrets)`.

### Task 5: `aidlc adopt --import`, the reviewed patch

**Files:**
- Modify: `cli/aidlc/adopt.py` (`import_patch`)
- Test: `tests/unit/test_adopt_import.py`

**Interfaces:** `adopt.import_patch(repo) -> tuple[str, list[str]]` returns a patch that `git apply` accepts, plus the problems (the items it left alone). It raises `AdoptError` before `init-repo`.

**What the patch does:**

| Source | Destination |
|---|---|
| `CLAUDE.md` (hand-written), `.github/copilot-instructions.md`, `.cursorrules` | a section appended to `AGENTS.md`, headed `## Imported from <file> (review: keep what every tool needs)`; the source is deleted |
| `.cursor/rules/<n>.mdc` with `globs` | `.aidlc/rules/<n>.md` with `paths:` from the globs; without globs, or with `alwaysApply: true`, appended to `AGENTS.md` |
| `.github/instructions/<n>.instructions.md` with `applyTo` | `.aidlc/rules/<n>.md` with `paths:` from the comma-separated globs |

A destination that already exists is never overwritten. That item is listed as a problem, and left in place.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_adopt_import.py
import subprocess
import unittest
from datetime import date

from aidlc import adopt
from aidlc.repo import init_repo
from tests.helpers import TempRepo, git


class ImportPatchTest(unittest.TestCase):
    FILES = {"CLAUDE.md": "Run pytest before you push.\n",
             ".cursor/rules/api.mdc": "---\nglobs: src/api/**, src/routes/**\nalwaysApply: false\n---\nKeep handlers thin.\n",
             ".github/instructions/db.instructions.md": "---\napplyTo: 'db/**'\n---\nNo raw SQL.\n",
             ".github/copilot-instructions.md": "Prefer small functions.\n"}

    def test_refuses_before_init_repo(self):
        with TempRepo(self.FILES) as root, self.assertRaises(adopt.AdoptError):
            adopt.import_patch(root)

    def test_the_patch_applies_and_never_overwrites(self):
        with TempRepo(self.FILES) as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            (root / ".aidlc/rules/db.md").write_text("---\npaths: [db/**]\n---\nPerson's rule.\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "init")
            patch, problems = adopt.import_patch(root)
            self.assertEqual(len(problems), 1)
            self.assertIn(".aidlc/rules/db.md", problems[0])
            (root / "adopt.patch").write_text(patch, encoding="utf-8")
            done = subprocess.run(["git", "apply", "--check", "adopt.patch"], cwd=root, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            git(root, "apply", "adopt.patch")
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            for needle in ("## Imported from CLAUDE.md", "Run pytest before you push.",
                           "## Imported from .github/copilot-instructions.md"):
                self.assertIn(needle, agents)
            api = (root / ".aidlc/rules/api.md").read_text(encoding="utf-8")
            self.assertIn('  - "src/api/**"', api)
            self.assertIn('  - "src/routes/**"', api)
            self.assertIn("Keep handlers thin.", api)
            self.assertFalse((root / "CLAUDE.md").exists())
            self.assertFalse((root / ".cursor/rules/api.mdc").exists())
            self.assertTrue((root / ".github/instructions/db.instructions.md").exists())   # left: its target exists
            self.assertEqual((root / ".aidlc/rules/db.md").read_text(encoding="utf-8"),
                             "---\npaths: [db/**]\n---\nPerson's rule.\n")

    def test_nothing_to_import_is_an_empty_patch(self):
        with TempRepo({"README.md": "x\n"}) as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            self.assertEqual(adopt.import_patch(root), ("", []))
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_adopt_import -v`. Expected: `AttributeError` (no `import_patch`).
- [ ] **Step 3: Implement.** Add to `adopt.py`:

```python
import difflib
import json

from .templates import TemplateError, parse_front_matter


def _diff(rel: str, old: str | None, new: str | None) -> str:
    """One file's change in the form `git apply` reads."""
    a = [] if old is None else old.splitlines(keepends=True)
    b = [] if new is None else new.splitlines(keepends=True)
    head = [f"diff --git a/{rel} b/{rel}\n"]
    if old is None:
        head.append("new file mode 100644\n")
    if new is None:
        head.append("deleted file mode 100644\n")
    body = difflib.unified_diff(a, b, "/dev/null" if old is None else f"a/{rel}",
                                "/dev/null" if new is None else f"b/{rel}")
    out = "".join(head)
    for line in body:
        out += line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
    return out


def _rule(paths: list[str], body: str) -> str:
    return "---\npaths:\n" + "".join(f"  - {json.dumps(p)}\n" for p in paths) + "---\n" + body.lstrip("\n")


def _globs(value: object) -> list[str]:
    items = value if isinstance(value, list) else str(value or "").split(",")
    return [g.strip().strip("'\"") for g in items if isinstance(g, str) and g.strip()]


def import_patch(repo: Path) -> tuple[str, list[str]]:
    if not (repo / CONFIG).is_file():
        raise AdoptError("run `aidlc init-repo` first: the import appends to its AGENTS.md")
    agents_old = (repo / "AGENTS.md").read_text(encoding="utf-8")
    appended, changes, problems = "", [], []
    for rel, _tool, action in survey(repo).agent_config:
        if action != "import":
            continue
        text = (repo / rel).read_text(encoding="utf-8")
        target = None
        if rel.endswith((".mdc", ".instructions.md")):
            try:
                meta, body = parse_front_matter(text, repo / rel)
            except TemplateError:
                meta, body = {}, text
            paths = _globs(meta.get("globs") if rel.endswith(".mdc") else meta.get("applyTo"))
            if paths and not meta.get("alwaysApply"):
                name = PurePosixPath(rel).name.removesuffix(".mdc").removesuffix(".instructions.md")
                target = f".aidlc/rules/{name}.md"
                if (repo / target).exists():
                    problems.append(f"{rel}: {target} already exists; merge it by hand (nothing overwritten)")
                    continue
                changes.append((target, None, _rule(paths, body)))
            else:
                text = body
        if target is None:
            appended += f"\n## Imported from {rel} (review: keep what every tool needs)\n\n{text.rstrip()}\n"
        changes.append((rel, (repo / rel).read_text(encoding="utf-8"), None))
    if appended:
        changes.insert(0, ("AGENTS.md", agents_old, agents_old.rstrip("\n") + "\n" + appended))
    return "".join(_diff(rel, old, new) for rel, old, new in changes), problems
```

When `AGENTS.md` has a `<!-- … -->` marker or a size budget, the drift check reports any growth past the budget. That is intended: the person trims the imported section.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_adopt -v` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(adopt): aidlc adopt --import prints a reviewed patch moving CLAUDE.md, Copilot and Cursor rules into AGENTS.md and .aidlc/rules/`.

### Task 6: The `aidlc-adopt` skill, the adoption guide, and ADR 0007

**Files:**
- Create:
  - `core/skills/aidlc-adopt/SKILL.md`;
  - `docs/adoption/README.md`;
  - `docs/adr/0007-adoption-and-ratchet.md`;
  - `tests/unit/test_adoption_docs.py`.
- Modify:
  - `tests/unit/test_skills_format.py`: add `aidlc-adopt` to no list. `EXPECTED_5A` stays as it is; the format tests cover every skill automatically.
  - `docs/codebase-map.md` (areas `cli/aidlc/adopt.py`, `cli/aidlc/baseline.py`, `core/context/stack-hints.yaml`);
  - `README.md` (link);
  - `docs/skills/README.md` (the skills table);
  - `docs/harness/README.md` (one line on the baseline);
  - regenerate `plugins/aidlc/` and `docs/traceability.md`.

- [ ] **Step 1: Write the failing test.**

```python
# tests/unit/test_adoption_docs.py
import unittest

from aidlc.paths import framework_root
from aidlc.templates import parse_front_matter

ROOT = framework_root()


class AdoptionDocsTest(unittest.TestCase):
    def test_guide_covers_the_flow(self):
        text = (ROOT / "docs/adoption/README.md").read_text(encoding="utf-8")
        for needle in ("aidlc adopt", "aidlc init-repo", "--import", "git apply", ".aidlc/baseline.yaml",
                       "report_only", "may only shrink", "review_by", "never baselined", "legacy_paths",
                       "required checks", "generic"):
            self.assertIn(needle, text)

    def test_adr_records_the_decision(self):
        text = (ROOT / "docs/adr/0007-adoption-and-ratchet.md").read_text(encoding="utf-8")
        for needle in ("ratchet", "baseline", "secrets", "report-only", "profile", "agent-skills"):
            self.assertIn(needle, text)

    def test_the_adopt_skill_is_manual(self):
        path = ROOT / "core/skills/aidlc-adopt/SKILL.md"
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path)
        self.assertEqual(meta["metadata"]["invocation"], "manual")
        for needle in ("aidlc adopt", "--import", "aidlc-context-setup", "baseline"):
            self.assertIn(needle, body)
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_adoption_docs -v`. Expected: `FileNotFoundError`.
- [ ] **Step 3: Write the skill and the docs.**

`core/skills/aidlc-adopt/SKILL.md`. Its front matter:
- `name: aidlc-adopt`;
- `description: "Walks an existing repository through adopting aidlc: survey, scaffold, import other tools' rule files, record today's debt as a baseline, and open the adoption pull request. Use when a repository that already has code joins the framework."`;
- `metadata`: `stage: context`, `invocation: manual`, `guide: ["16.5", "2.8", "15.7", "4.2"]`.

Its body has every required section (When to use, Inputs, Steps, Produces, Gate, Stop if, Common excuses, Red flags, Rules), the injection rule and the SAVES sentence word for word. The steps:
1. run `aidlc adopt` and read the report; stop on any secret (the person rotates and removes it);
2. the person runs `aidlc init-repo` with the profile the report suggests, or `generic` with the suggested commands;
3. `aidlc adopt --import`: the person reads and applies the patch;
4. hand over to `aidlc-context-setup` for `AGENTS.md` and the codebase map;
5. run `aidlc check`, and draft `.aidlc/baseline.yaml` in the reply for what fails today. Each entry gets an owner, a review date and a reason. Never `test`, `build` or secrets;
6. propose `legacy_paths` for code without tests;
7. the person opens the adoption pull request. After it merges, the owner switches on the required checks.

Common excuses include "baseline everything so CI is green", "the old secret is in history only, so it's fine" and "this skipped test will be fixed later, without a date".

`docs/adoption/README.md` covers:
- the flow diagram from this plan;
- what each step writes;
- the baseline file format, with both kinds (report-only steps and skips);
- the ratchet rules: new entries fail, expired entries fail, moving a date is a code-owner-reviewed decision, a new step may start report-only;
- secrets are never baselined;
- `legacy_paths`;
- why the adoption pull request is merged before the required checks are switched on;
- `generic` plus the suggested commands for any stack.

`docs/adr/0007-adoption-and-ratchet.md` (Accepted, 2026-10-23):
- **Context:** red forever, unmanaged config of other tools (ADR 0006), guide 16.5.
- **Decision:** the survey, the import patch, the baseline and ratchet, `legacy_paths`, no profiles per stack, and secrets fixed first.
- **Consequences:** an expired entry turns every pull request red until it is fixed or its owner moves the date; the local `aidlc check` honours the baseline but does not run the ratchet (CI does); the adoption pull request is reviewed without the trusted CI.
- **Credit:** the ratchet idea comes from addyosmani/agent-skills (MIT); the text is our own.

Run `bin/aidlc plugin build` and `bin/aidlc trace`.
- [ ] **Step 4: Run the tests and the checks, and watch them pass.** Run the Step 2 command, `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_skills_format tests.unit.test_plugin -v`, `bin/aidlc plugin build --check`, `bin/aidlc trace --check`, `bin/aidlc check context-drift .` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `docs(adopt): ADR 0007, the adoption guide and the aidlc-adopt skill`.

### Task 7: Live proof on a scratch existing repository (no model, no cost)

**Files:**
- Create: `docs/verification/<date>-adoption.md`

- [ ] **Step 1: Build the scratch repository.** Create it in the session scratchpad, never in the framework repository. It holds:
  - a small Python package with three `unittest` tests, one of them skipped;
  - a hand-written `CLAUDE.md`;
  - a `.cursor/rules/api.mdc` with globs;
  - a `.github/workflows/ci.yml`;
  - a lint command that fails (`python3 -c "raise SystemExit(1)"`, standing in for an existing lint debt).

  Commit it with the noreply identity.
- [ ] **Step 2: Walk the flow.**
  1. `bin/aidlc adopt <scratch>`;
  2. `bin/aidlc init-repo <scratch> --profile generic …`, then set the suggested commands in `.aidlc/config.yaml`;
  3. `bin/aidlc adopt --import <scratch> > adopt.patch`, then `git apply`;
  4. `bin/aidlc render --tool claude-code <scratch>`;
  5. `bin/aidlc check` in the scratch repository: expect lint FAIL and skips FAIL;
  6. write `.aidlc/baseline.yaml` (lint report-only, the skip baselined);
  7. `bin/aidlc check` again: expect PASS, with lint "reported".

  Record each command's exit code and the step lines.
- [ ] **Step 3: Write the evidence.**
  - What ran, with the outputs abridged.
  - **Not verified:** the ratchet in a real trusted CI run. It runs in Plan 6, where the demo's existing repository adopts through a real pull request.

  Commit it.

---

## Self-review notes

- **Spec coverage:**

  | Agreed piece | Task |
  |---|---|
  | survey | 4 |
  | import patch | 5 |
  | baseline | 1 |
  | ratchet | 2 |
  | two-speed rule | 3 |
  | skill | 6 |
  | no new profiles | stack hints suggest `generic` and its commands |
  | secrets never baselined | the baseline has no secrets kind; the survey exits 1 |

- **Deliberately later:**
  - enforcing `legacy_paths` in the checks (the Legacy plan);
  - baselines for other judge steps (none: they are the harness);
  - Java and Go profiles (data, when a team asks);
  - a new-project mode (`init-repo` already covers it).
- **Placeholder scan.** Task 6's docs are described by their required content and checked by needles; everything else is given in full.
- **Type consistency.** `Entry.kind` is `report_only` or `skips` throughout. `BASELINE` is one constant, used by onecheck, ci and the tests. `REPORTED` is the only new status.
