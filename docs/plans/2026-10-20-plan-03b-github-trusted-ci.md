# Plan 3.5: GitHub as the trusted CI. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GitHub Actions on public repositories becomes the trusted CI. Local `aidlc ci` becomes a clearly labelled preview. The local-trust machinery is removed, and one real pull request proves the gates on GitHub.

**Architecture:**
- **Unchanged:** the gates. `aidlc check`, the judges, the bubblewrap sandbox and the hooks stay as they are.
- **Trusted mode:** GitHub mode (`aidlc ci --trusted … --head …`, which the rendered workflow calls) is the only trusted mode.
- **Local mode:** it keeps its worktrees and sandbox, so the change's code still never runs unsandboxed on your machine. It makes no trust claim:
  - its base comes from the working copy;
  - its record is labelled `local-preview`;
  - it never says "merge-ready".
- **Removed:** the code that existed only to make local runs trustworthy (the pinned base, `--accept-base`, the trusted base record, `--trusted-base` and approved-merges). The framework repository gets its own CI workflow and is published to `github.com/prashantsharma18/aidlc`. A small sample repository proves the rendered workflow on real pull requests.

**Tech Stack:** Python 3.12 (stdlib + PyYAML + jsonschema), GitHub Actions, `gh` CLI 2.102 (logged in as `prashantsharma18` over SSH).

**Spec:** the user's decision of 2026-10-20, which changes design D3. Task 1 records it as `docs/adr/0002-github-trusted-ci.md` and amends `docs/design/2026-10-18-aidlc-framework-design.md`. The decision:
- trusted CI runs on a real Git host the agent cannot reach, using public repos under `prashantsharma18`;
- local `aidlc ci` is a preview only;
- the local-trust machinery is removed.

## Global Constraints

- Every commit uses `prashantsharma18 <6386481+prashantsharma18@users.noreply.github.com>`, set per repository with `git config --local`. Never use the global work identity, and never change `~/.gitconfig`.
- Nothing secret is committed or pushed. Before every push, run the pre-push scan (Task 4, Step 1). It must report zero identity and zero secret findings.
- Public repositories only, under `github.com/prashantsharma18`. Create a repository, push to it, or change its settings only after the controller has the user's explicit go-ahead for that step.
- Python 3.12: the standard library plus PyYAML and jsonschema only. Hooks use the standard library only. Fail closed.
- Never change an assertion in a test older than Plan 3 (base `884022a`). ADR 0002 authorises removing the Plan 3 tests that test behaviour this plan removes. Each removal is listed by name in the task that owns it.
- A deny rule in `core/policy/permissions.yaml` is removed only when ADR 0002 removes the thing it guards. That applies to one rule: `aidlc scope*--accept-base*`.
- Actions are pinned by full commit SHA, with the tag in a comment. Reuse the SHAs already in `core/ci/github/aidlc-verify.yml` and `setup.yaml`.
- `make test`, `make policy-test` (with `AIDLC_TOOLS_DIR`), `make sandbox-test`, `bin/aidlc trace --check`, `bin/aidlc check context-drift .`, `bin/aidlc policy validate` and `bin/aidlc render --tool claude-code --check .` must all pass before each commit that touches code.

## Review Focus

1. **A person mistakes the local preview for a verdict.** Nothing local may print or record "merge-ready", `simulated-ci`, or "evidence". Pinned by Task 2's `test_local_record_is_a_preview_without_merge_ready` and `test_local_cli_says_preview`.
2. **GitHub mode loses a trust property while local mode is simplified.** These must still hold:
   - the records directory must be fresh and outside the PR checkout;
   - `--head-sha` must equal the checkout;
   - `--sandbox auto` is allowed only for `scans`.

   Pinned by the existing `test_ci.py` GitHub-mode tests, which this plan must not change. Task 2 lists them as kept.
3. **A stale `entry/<repo>-<hash8>.base.json` from an earlier install changes behaviour.** Nothing may read it. Pinned by Task 2's `test_a_leftover_base_record_is_ignored`.
4. **The first push leaks the work email or a secret.** Pinned by Task 4, Step 1: a scan that must print `0` for each check before any push.
5. **The public framework workflow runs on fork pull requests.** It must hold no secrets and only a read token. Pinned by Task 3's `test_framework_workflow_is_read_only_and_pinned`.

---

### Task 1: ADR 0002 and the design amendment

**Files:**
- Create: `docs/adr/0002-github-trusted-ci.md`
- Modify:
  - `docs/design/2026-10-18-aidlc-framework-design.md`: the D3 row (line 42), "Labels every result `simulated-ci`" (line 319), the §12 note, and the risk row (line 419)
  - `docs/adr/0001-policy-as-code.md`: one line under Consequences pointing to ADR 0002

**Interfaces:** Produces the decision text that Tasks 2–5 cite.

- [ ] **Step 1: Write ADR 0002.** Write it in the style of ADR 0001: Status, Context, Decision, Consequences. It must say all of the following:
  - **Context.**
    - D3 put trusted CI on the developer's machine because no Git host existed.
    - Plan 3's reviews then found that a trusted runner sharing the agent's machine, user and `.git` kept producing bypasses. The clearest was an agent forging `refs/heads/main` to get a false "merge-ready yes".
    - Hardening against that cost about 300 lines of code plus tests, with no value once a real host exists.
  - **Decision.**
    - Trusted CI is GitHub Actions, on public repositories under `github.com/prashantsharma18`.
    - Merge readiness is GitHub's: required status checks (`compile`, `check`, `scans`) and pull-request rules.
    - Local `aidlc ci` is a preview, labelled `local-preview`, with no merge-ready claim.
    - Removed: the trusted base record and `aidlc render --trusted-base`; the pinned-base check in local CI; `aidlc scope --accept-base` and its deny rule; `plans/approved-merges.txt`.
    - Kept: every gate, the sandbox, the hooks, GitHub mode and the generated-file judge.
  - **Consequences.**
    - The agent never holds a push credential for these repositories.
    - Commits use the noreply identity.
    - The repositories are public, so nothing secret may be committed: the pre-push scan is mandatory.
    - A forged local base now only misleads the local preview and the local guard's scope; GitHub's scope step reads approvals from the pull request's base commit.
    - Branch protection is real: rulesets on `main`.
- [ ] **Step 2: Amend the design.**
  - Rewrite the D3 row to say "trusted CI on GitHub (ADR 0002)".
  - Change line 319 to: labels local results `local-preview`; GitHub runs carry `github-actions`.
  - Change the risk row at line 419 to "Branch protection enforced by GitHub rulesets (ADR 0002)".
  - Add one sentence under §12: "ADR 0002 (2026-10-20) moves trusted CI to GitHub; Plan 3.5 implements it."
- [ ] **Step 3: Check.** Run `bin/aidlc trace --check && bin/aidlc check context-drift .`. Expected: `0 problems` and `0 fail`.
- [ ] **Step 4: Commit.**

```bash
git add docs/adr/0002-github-trusted-ci.md docs/adr/0001-policy-as-code.md docs/design/2026-10-18-aidlc-framework-design.md
git commit -m "docs(adr): 0002 GitHub is the trusted CI; local aidlc ci is a preview (amends design D3)"
```

### Task 2: Local `aidlc ci` becomes a preview, and the local-trust code goes

**Files:**
- Modify:
  - `cli/aidlc/ci.py`:
    - remove `pinned_base`, `NO_BASE`, `MERGES`, `_merge_ready`, the `merges` read and `recorded_base`;
    - remove the `base_moves` import;
    - labels per mode.
  - `cli/aidlc/commands/ci_cmd.py`: the output lines.
  - `cli/aidlc/cliinfo.py`: remove `base_file`, `record_base` and `recorded_base`.
  - `cli/aidlc/commands/render_cmd.py`: remove `_trusted_base` and `--trusted-base`.
  - `cli/aidlc/commands/scope_cmd.py`: remove `_confirmed_base` and `--accept-base`. `_run` pins `base_commit(repo, base)` directly, as before Plan 3's final wave.
  - `cli/aidlc/scope.py`: remove `base_moves`, `EVIDENCE`, `NO_DRIVERS` (if nothing else uses it) and `_UNPRINTABLE` (same condition).
  - `core/policy/permissions.yaml`: remove `"aidlc scope*--accept-base*"`, then regenerate `tests/fixtures/render/claude-code/settings.node.json` with the renderer.
  - `core/policy/branch-protection.yaml` and `core/schemas/branch-protection.schema.json`: drop `/plans/approved-merges.txt` from `code_owned_paths` and from the schema's required items.
  - `core/ci/github/aidlc-verify.yml`: drop `/plans/approved-merges.txt` from the header comment.
- Test: `tests/unit/test_ci.py`, `tests/unit/test_ci_templates.py`

**Interfaces:**
- Produces:
  - `ci.LOCAL_LABEL = "local-preview"` and `ci.GITHUB_LABEL = "github-actions"`.
  - `CiPlan.label: str`, with default `GITHUB_LABEL`.
  - The record drops `merge_ready` and `merge_ready_reason`.
  - `ci_local(repo, branch, group)` keeps its signature.
- Consumes: `harness.base_branch` (imported as `configured_base`) and `scope.base_commit`.

**Tests removed (behaviour removed by ADR 0002; list each one in the report):**
- `PinnedBaseTest` (all 4 tests)
- `TrustedBaseRenderTest` (all 5)
- `CiPinnedScopeBaseTest` (both)
- `AcceptBaseTest` (all 5)
- `CiTest.test_merge_ready_needs_an_approval_for_this_exact_head`
- `CiFixRound1Test.test_the_recorded_base_judges_even_when_the_branch_config_names_another`

**Tests edited (only the lines that read `merge_ready` or `MERGES`; every other assertion stays):**
- `CiTest.test_passing_branch_records_simulated_ci_and_cleans_up`: rename it to `test_passing_branch_records_a_local_preview_and_cleans_up`, and assert `record["label"] == "local-preview"`.
- `CiTest.test_tests_that_try_to_rewrite_their_judges_change_nothing`: drop the approved-merges fixture line and the `merge_ready` assertion. Keep every sandbox assertion.
- `CiTest.test_groups`: drop the `merge_ready` assertion.
- `CiFixRound1Test.test_a_tracked_record_in_the_head_is_refused`: drop the `merge_ready` read.
- `test_ci_templates.py`: two lines list `/plans/approved-merges.txt`. Remove it from both lists.

**Kept unchanged:** every GitHub-mode test in `test_ci.py` (fresh records, head SHA, auto sandbox, `GITHUB_ACTIONS`). Run `grep -n "ci_checkouts" tests/unit/test_ci.py` to list them in the report.

- [ ] **Step 1: Write the failing tests** in `tests/unit/test_ci.py`, in a new class `LocalPreviewTest`. Use the same fixtures the existing local `CiTest` uses: its setUp builds a repo with a passing test step and a scope, and skips when bwrap is unavailable through the existing `NEEDS_SANDBOX` decorator.

```python
@NEEDS_SANDBOX
class LocalPreviewTest(CiTest):          # reuse CiTest's repo, scope and helpers
    def test_local_record_is_a_preview_without_merge_ready(self):
        result, record, path = ci.ci_local(self.root, BRANCH, None)
        self.assertEqual(record["label"], "local-preview")
        self.assertNotIn("merge_ready", record)
        self.assertNotIn("merge_ready_reason", record)
        self.assertTrue(ci.verify_record(json.loads(path.read_text())))

    def test_local_cli_says_preview(self):
        code, out, err = run_cli("ci", "--repo", str(self.root), "--branch", BRANCH)
        self.assertNotIn("merge-ready", out + err)
        self.assertNotIn("simulated-ci", out + err)
        self.assertIn("local preview", out)
        self.assertIn("trusted CI is GitHub Actions", out)

    def test_a_leftover_base_record_is_ignored(self):
        guard = hooks().guard
        stale = guard.entry_file(self.root).with_name(guard.entry_file(self.root).stem + ".base.json")
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text('{"base_branch": "not-a-real-branch"}')
        result, record, _ = ci.ci_local(self.root, BRANCH, None)
        self.assertEqual(record["base_branch"], "main")

    def test_render_has_no_trusted_base_and_scope_has_no_accept_base(self):
        code, _, err = run_cli("render", "--tool", "claude-code", str(self.root), "--trusted-base", "main")
        self.assertEqual(code, 2)
        code, _, err = run_cli("scope", "--repo", str(self.root), "--branch", BRANCH, "--accept-base", "0" * 40)
        self.assertEqual(code, 2)
```

Adapt the helper names (`BRANCH`, `self.root`, `run_cli` and `hooks`) to the ones `test_ci.py` already uses; read its imports first. The assertions stay as written.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_ci.LocalPreviewTest -v`. Expected: FAIL with `KeyError: 'label'` or an "unexpected" `merge_ready`, and `--trusted-base` is accepted.
- [ ] **Step 3: Implement.** In `ci.py`, replace `LABEL`, `MERGES`, `NO_BASE` and the `recorded_base` import with the code below, and add `label: str = GITHUB_LABEL` to `CiPlan`.

```python
LOCAL_LABEL = "local-preview"       # ADR 0002: a local run is a preview, never evidence
GITHUB_LABEL = "github-actions"     # the trusted run: GitHub mode inside GitHub Actions
```

In `run_ci`, make these changes:
- delete `merges = _read_trusted(plan.trusted / MERGES)` and the `_merge_ready` call;
- build the record with `"label": plan.label` and no `merge_ready` keys;
- change the base-mismatch message to:
  `f"the base branch's configuration names base '{named}', not '{plan.base_branch}'"`.

Delete `_merge_ready` and `pinned_base`. Then replace `ci_local`'s base lines with:

```python
    base_branch = configured_base(repo)           # a preview: the working copy's own setting (ADR 0002)
    ...
    base = base_commit(repo, base_branch)
    ...
        plan = CiPlan(repo=repo, branch=branch, head=head, trusted=trusted, work=work,
                      base_branch=base_branch, base=base, records=records, label=LOCAL_LABEL)
```

In `ci_cmd.py`, update the module docstring to `"""aidlc ci: the gates against a task branch. GitHub mode is the trusted CI (ADR 0002); local mode is a preview."""`. Then replace the two print lines with:

```python
    if record["label"] == LOCAL_LABEL:
        print(f"ci  record {path}  (local preview: not evidence; trusted CI is GitHub Actions)")
    else:
        print(f"ci  record {path}  ({GITHUB_LABEL})")
```

Then make the deletions and edits listed under **Files**:
- In `scope_cmd._run`, use `live = base_commit(repo, base)` and drop `--accept-base`.
- In `render_cmd`, drop `_trusted_base` and its call. Also drop the `--trusted-base` argument, and the `args.trusted_base` checks in `_run`.
- In `cliinfo`, drop the three base functions.
- In `scope.py`, drop `base_moves` and its constants, after checking with `grep -rn` that nothing else uses them.
- Remove the deny line from `permissions.yaml`, then regenerate the golden fixture with the renderer, as Plan 3 Task 4 did.
- Edit `branch-protection.yaml`, the schema and the workflow template header.
- Update the existing tests exactly as listed above.
- [ ] **Step 4: Run every check.** Expected: `make test` passes, with the same 13 skips as before when `AIDLC_TOOLS_DIR` is unset. `make policy-test` and `make sandbox-test` pass with `AIDLC_TOOLS_DIR=…/tools-live`. trace, drift, validate and `render --check` are clean. Also run `git diff 884022a -- tests/ | grep '^-.*assert'`: every removed assertion must belong to a test this task lists.
- [ ] **Step 5: Commit.** Stage the explicit paths and commit with `refactor(ci): local aidlc ci is a preview; remove the local-trust machinery (ADR 0002)`.

### Task 3: CI for the framework itself

**Files:**
- Create:
  - `.github/workflows/framework-ci.yml`
  - `.github/CODEOWNERS`, containing `* @prashantsharma18`
- Test: `tests/unit/test_framework_workflow.py`

**Interfaces:** Produces the check names that Task 4's ruleset requires: `unit`, `sandbox` and `policy`.

- [ ] **Step 1: Write the failing test.**

```python
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/framework-ci.yml"
PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


class FrameworkWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.on = self.wf.get("on", self.wf.get(True))      # YAML 1.1 reads a bare `on` as True

    def test_framework_workflow_is_read_only_and_pinned(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(self.wf["permissions"], {"contents": "read"})
        self.assertNotIn("secrets.", text)
        self.assertNotIn("pull_request_target", text)
        for job in self.wf["jobs"].values():
            self.assertNotIn("permissions", job)
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], PINNED)
                if "actions/checkout" in step.get("uses", ""):
                    self.assertFalse(step["with"]["persist-credentials"])
                self.assertNotIn("${{", step.get("run", ""))

    def test_jobs_and_triggers(self):
        self.assertEqual(set(self.wf["jobs"]), {"unit", "sandbox", "policy"})
        self.assertEqual(set(self.on), {"push", "pull_request"})
        self.assertEqual(self.on["push"]["branches"], ["main"])
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_framework_workflow -v`. Expected: `FileNotFoundError`.
- [ ] **Step 3: Write the workflow.** Use the checkout SHA `3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1), which `aidlc-verify.yml` already pins.

```yaml
# CI for the aidlc framework itself (ADR 0002). Read-only token, no secrets, actions pinned by SHA.
name: framework-ci
on:
  push: {branches: [main]}
  pull_request:
permissions: {contents: read}
concurrency: {group: "framework-ci-${{ github.ref }}", cancel-in-progress: true}
jobs:
  unit:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with: {persist-credentials: false}
      - run: sudo apt-get update -q && sudo apt-get install -y -q python3-yaml python3-jsonschema bubblewrap
      - run: make test
  sandbox:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with: {persist-credentials: false}
      - run: sudo apt-get update -q && sudo apt-get install -y -q python3-yaml python3-jsonschema bubblewrap
      - run: sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 || true
      - run: make sandbox-test
  policy:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with: {persist-credentials: false}
      - run: sudo apt-get update -q && sudo apt-get install -y -q python3-yaml python3-jsonschema
      - run: bin/aidlc tools install --dir "$RUNNER_TEMP/aidlc-tools"
      - run: AIDLC_TOOLS_DIR="$RUNNER_TEMP/aidlc-tools" make policy-test
```

- [ ] **Step 4: Run it and watch it pass.** Run the same command as Step 2. Then run `make test`. Expected: both PASS.
- [ ] **Step 5: Commit** with `ci(framework): read-only, SHA-pinned workflow for unit, sandbox and policy tests; CODEOWNERS`.

### Task 4: Publish the framework repository (controller, with the user's go-ahead)

**Files:**
- Modify: none. Settings on GitHub only.

- [ ] **Step 1: Run the pre-push scan.** Each line must print `0`.

```bash
git log --all --format='%ae%n%ce' | grep -vc '^6386481+prashantsharma18@users.noreply.github.com$'
# The personal patterns are read at run time, so none of them is ever written into the repository.
git log --all -p | grep -ciF -e "$(git config --global user.email)" -e "$HOME"
git log --all -p | grep -cE 'ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|sk-ant-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----[A-Za-z0-9+/=\n]{40}'
git ls-files | grep -ciE '(^|/)\.env($|\.)|\.pem$|\.key$|id_rsa'
```

- [ ] **Step 2: Ask the user.** Get their go-ahead before creating the repository and pushing. Then run:

```bash
gh repo create prashantsharma18/aidlc --public --description "AI-native SDLC framework: from intent to verified change"
git remote add origin git@github.com:prashantsharma18/aidlc.git
git push -u origin main
```

- [ ] **Step 3: Turn on push protection.**

```bash
gh api -X PATCH repos/prashantsharma18/aidlc -f "security_and_analysis[secret_scanning][status]=enabled" -f "security_and_analysis[secret_scanning_push_protection][status]=enabled"
```

- [ ] **Step 4: Watch the first framework CI run.** Run `gh run watch --exit-status $(gh run list --workflow framework-ci.yml --limit 1 --json databaseId -q '.[0].databaseId')`. Expected: `unit`, `sandbox` and `policy` all succeed. If any job fails, fix the cause on a branch, open a pull request, and record the cause in the ledger.
- [ ] **Step 5: Ask the user.** Get their go-ahead before adding the ruleset. Then add a ruleset on `main`: require a pull request (0 approvals, because the owner works alone), require the status checks `unit`, `sandbox` and `policy`, and block force-pushes and deletion.

```bash
gh api -X POST repos/prashantsharma18/aidlc/rulesets --input - <<'EOF'
{"name": "main", "target": "branch", "enforcement": "active",
 "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
 "rules": [{"type": "deletion"}, {"type": "non_fast_forward"},
           {"type": "pull_request", "parameters": {"required_approving_review_count": 0, "dismiss_stale_reviews_on_push": false, "require_code_owner_review": false, "require_last_push_approval": false, "required_review_thread_resolution": false}},
           {"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": true, "required_status_checks": [{"context": "unit"}, {"context": "sandbox"}, {"context": "policy"}]}}]}
EOF
```

From here on, framework changes reach `main` only through pull requests. Record the repository URL and the ruleset id in the ledger.

A known limit, which the evidence doc and ADR 0002 must state: with one owner, required code-owner review cannot be turned on. GitHub does not let you approve your own pull request, so every merge would block. CODEOWNERS is in place for when a second reviewer exists. Until then, the controls are the required checks, the pull-request rule, and the agent holding no push credential.

### Task 5: Live proof on a sample repository (controller, with the user's go-ahead)

**Files:**
- Create, outside the framework:
  - `~/demos/aidlc-ci-sample/`, a node-profile repository: `package.json` with no dependencies, `package-lock.json` from `npm install`, `.nvmrc` containing `22`, `src/app.js`, `test/app.test.js`, and the rendered harness and workflow.
- Create, in the framework:
  - `docs/verification/2026-10-20-github-ci-proof.md`
- Modify: none in the framework's code.

- [ ] **Step 1: Build the sample.**
  1. Run `git init` and set the local identity (Global Constraints).
  2. Run `bin/aidlc init-repo` with the `node` profile, then set `ci: [github]` in `.aidlc/config.yaml`.
  3. Set these commands:
     - `commands.test`: `node --test --test-reporter=junit --test-reporter-destination=.check/test-report.xml`
     - `commands.lint` and `commands.typecheck`: `node --check src/app.js`
     - `test_reports`: `[".check/test-report.xml"]`
  4. Add `.github/CODEOWNERS` with `* @prashantsharma18`.
  5. Run `bin/aidlc render --tool claude-code .`.
  6. Write a task bundle, and commit its approval in `plans/approved-bundles.txt` with the full SHA.
  7. Run `bin/aidlc check`. Expected: `result PASS`.
- [ ] **Step 2: Publish the sample.** Run the Task 4 Step 1 scan on the sample; expect `0` on every line. Ask the user for their go-ahead. Then:
  1. Run `gh repo create prashantsharma18/aidlc-ci-sample --public` and push `main`.
  2. Run `gh variable set AIDLC_FRAMEWORK_REPO -b prashantsharma18/aidlc`.
  3. Run `gh variable set AIDLC_FRAMEWORK_REF -b <framework main SHA>`.
  4. Add a ruleset that requires `compile`, `check` and `scans`, using the Task 4 Step 5 body with those three contexts.
- [ ] **Step 3: Pull request A, an honest in-scope change.** Edit `src/app.js` and add a test line. Expected: `compile`, `check` and `scans` all succeed, and the PR is mergeable.
- [ ] **Step 4: Pull request B, which weakens an existing test.** Change an existing assertion in `test/app.test.js`. Expected:
  - `check` fails, with `protected-tests FAIL` in the job log;
  - GitHub shows the PR as blocked by the failing required check.
- [ ] **Step 5: Write the evidence.** Write `docs/verification/2026-10-20-github-ci-proof.md` with:
  - both PR URLs;
  - the run URLs, and the job result for each;
  - the `protected-tests` log line;
  - the ruleset id;
  - the framework SHA used.

  Commit it on a framework branch, open a pull request, and merge it once `framework-ci` is green.

---

## Self-review notes

- **Spec coverage:**
  - Trusted CI on GitHub: Tasks 4 and 5.
  - Local becomes a preview: Task 2.
  - Remove the local trust machinery: Task 2. These items are removed: `pinned_base`, `--accept-base`, `base_moves`, the base record, `--trusted-base`, approved-merges, and the deny rule.
  - The framework's own CI: Task 3.
  - Public and secret-free: the Task 4 scan.
  - The identity rule: Global Constraints.
  - D3 amended: Task 1.
- **Kept on purpose:**
  - the sandbox in local mode, which still protects the person's machine when it runs a branch's code;
  - the generated-file judge, the full-SHA approvals, and every GitHub-mode check.
- **Out of scope:**
  - the demo repositories (Plan 6);
  - evals and AI review jobs (Plan 4), which will be added to the same workflows;
  - the ledger's deferred minors.
