"""Plan 22: aidlc is instructions (ADR 0024). It ships no scripts and no CI workflows; the checks live in the
team's project; a verdict counts only from someone who did not write the change, at a named commit; and the words
need git, not a code host's features."""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = sorted(p.name for p in (ROOT / "skills").iterdir() if p.name.startswith("aidlc-"))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(read(rel).split())


def skill(name: str) -> str:
    return flat(f"skills/{name}/SKILL.md")


def section(text: str, heading: str) -> str:
    """One `## ` section of a whitespace-collapsed text."""
    return text.split(heading, 1)[1].split(" ## ", 1)[0]


AMENDED = ("0012-mechanical-recipe-commit", "0015-work-routes-and-the-part-model", "0016-greenfield-entry",
           "0017-feature-fast-path-and-build-modes", "0020-approved-documents-merge-first",
           "0021-several-repositories-at-least-tier-2", "0022-one-owner-per-fact-and-pinned-parts",
           "0023-people-decide-the-ai-records")


class AdrTest(unittest.TestCase):
    """Task 1: the decision is recorded before anything changes."""

    ADR = "docs/adr/0024-instructions-first.md"

    def test_adr_0024_is_proposed_and_supersedes_0019(self):
        text = read(self.ADR)
        self.assertRegex(text, r"Status: (Proposed|Accepted)")
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = " ".join(text.split())
        for phrase in ("Supersedes: ADR 0019", "It ships no scripts and no CI workflows to teams",
                       "A rule that must hold every time lives in the team's project",
                       "counts only from someone who did not write it", "`plans/<KEY>/review-evidence.md`",
                       "They keep Read, Grep and Glob, and never run a command",
                       "aidlc depends on git and on no code-host feature", "the tag `checks-v1`",
                       "\"Change request\" stays the name of route C"):
            self.assertIn(phrase, body, phrase)

    def test_adr_0024_holds_the_rule_table(self):
        text = read(self.ADR)
        self.assertIn("| Rule | Was enforced by | Now enforced by |", text)
        for rule in ("No deleted test, no changed assertion", "Plan complete before approval",
                     "Recipe commit is mechanical", "Contract version raised; breaking change raises MAJOR",
                     "Consumer copy matches the pinned version", "Secrets never read; push asks first"):
            self.assertIn(rule, text, rule)

    def test_adr_0019_is_superseded(self):
        self.assertIn("Status: Superseded by ADR 0024 (proposed, 2026-11-20)", read("docs/adr/0019-gates-enforced-by-code.md"))

    def test_each_amended_adr_carries_a_dated_note(self):
        for name in AMENDED:
            text = read(f"docs/adr/{name}.md")
            self.assertIn("Amended by ADR 0024 (2026-11-20): see the last section.", text, name)
            self.assertTrue(text.rstrip().split("\n## ")[-1].startswith("Amended by ADR 0024 (2026-11-20)"), name)
            self.assertIn("Status: Accepted", text, name)


VERDICT = ("- A verdict that the change is done or passes counts only from someone who did not write it: one of the "
           "`reviewer-*` agents, dispatched with the evidence file and the story documents it names, never the author's "
           "conversation; or a person other than the engineer who ran the session. It names the commit it judged (`git rev-parse HEAD`). A later "
           "commit that changes any path outside `plans/<KEY>/` voids it: `git diff --name-only <judged commit> HEAD "
           "-- ':(top)' ':(top,exclude)plans/<KEY>/'` must print nothing.")
REVIEWERS = ("reviewer-bug", "reviewer-security", "reviewer-compliance", "reviewer-tests")
EVIDENCE = "skills/aidlc-review/assets/review-evidence.md"


class EvidenceAndVerdictTest(unittest.TestCase):
    """Task 2: the session writes the evidence with git; reviewers who did not write the change read it, never run a
    command, and judge a named commit."""

    def test_the_template_says_what_the_session_writes_and_where(self):
        self.assertEqual(read(EVIDENCE), read("skills/aidlc-build/assets/review-evidence.md"))
        text = flat(EVIDENCE)
        for command in ("git rev-parse HEAD", "git merge-base HEAD origin/<default branch>", "git diff --stat --no-renames <base> HEAD",
                        "git diff --name-only --no-renames <base> HEAD", "git diff --no-renames <base> HEAD -- ':(top)<test path>'",
                        "git diff <base> HEAD -- ':(top)<manifest>'", "git diff <base> HEAD -- ':(top)plans/<KEY>/'",
                        "git worktree add <folder> <base>", "echo $?", "git -C <folder> diff --cached --stat <commit>"):
            self.assertIn(command, text, command)
        self.assertIn("to `plans/<KEY>/review-evidence.md`", text)
        self.assertIn("The reviewer agents read this file and never run a command.", text)

    def test_each_section_names_its_reader(self):
        text = read(EVIDENCE)
        for heading in ("## Changed files (reviewer-compliance)", "## Test files (reviewer-tests, reviewer-compliance)",
                        "## Test count (reviewer-tests)", "## Commands run at HEAD (reviewer-tests)",
                        "## Dependency manifests (reviewer-compliance)", "## Check configuration (reviewer-compliance)",
                        "## Story documents (reviewer-compliance)",
                        "## Added suppressions, skips and exceptions (reviewer-compliance)",
                        "## Recipe commits (reviewer-compliance)"):
            self.assertIn(heading, text, heading)
        for rel in ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md"):
            where = read(rel).split("## Where to look", 1)[1]
            self.assertIn("- Test paths, for the review evidence:", where, rel)
            self.assertIn("- Dependency manifests, for the review evidence:", where, rel)
            self.assertIn("- Check configuration, for the review evidence:", where, rel)

    def test_build_and_review_write_and_commit_it(self):
        for name in ("aidlc-build", "aidlc-review"):
            self.assertIn("  - review-evidence\n", read(f"skills/{name}/SKILL.md"), name)
            self.assertIn("write the evidence file `plans/<KEY>/review-evidence.md` from `assets/review-evidence.md` "
                          "and commit it on its own", skill(name), name)
            self.assertIn("each in a fresh context", skill(name), name)
        self.assertNotIn("slice check", skill("aidlc-build"))
        self.assertIn("TESTS BEFORE", read("skills/aidlc-build/assets/progress-note.md"))

    def test_the_reviewers_read_it_and_never_run_a_command(self):
        for name in ("reviewer-compliance", "reviewer-tests"):
            text = flat(f"agents/{name}.md")
            self.assertIn("`plans/<KEY>/review-evidence.md`", text, name)
            self.assertIn("You never run a command: you judge the outputs it holds.", text, name)
            self.assertIn("or a file written for another commit, is a high finding", text, name)
        self.assertNotIn("slice check", flat("agents/reviewer-compliance.md"))
        for name in REVIEWERS:
            front = read(f"agents/{name}.md").split("\n---", 1)[0]
            self.assertIn("\ntools: Read, Glob, Grep\n", front, name)
            self.assertIn("Start your Return with `Judged: <commit>`, the commit your brief names.",
                          flat(f"agents/{name}.md"), name)

    def test_a_verdict_comes_from_a_non_author_and_names_its_commit(self):
        for name in ("aidlc-build", "aidlc-verify", "aidlc-review"):
            self.assertIn(VERDICT, section(skill(name), "## Rules"), name)
        self.assertIn("Your STATUS `done` means your steps are finished, not that the change passes.",
                      section(skill("aidlc-build"), "## Gate"))

    def test_a_stale_verdict_is_void(self):
        stops = section(skill("aidlc-review"), "## Stop if")
        self.assertIn("A reviewer verdict names a commit that is not an ancestor of the pull request's head", stops)
        self.assertNotIn("other than the pull request's head", stops)
        self.assertIn("git merge-base --is-ancestor <judged commit> HEAD", stops)
        self.assertIn("the verdict is void", stops)
        record = read("skills/aidlc-review/assets/review-record.md")
        self.assertIn("at {{commit}}", record.split("## Reviewer verdicts", 1)[1])
        self.assertIn("one of the `reviewer-*` agents, dispatched with the evidence file and the story documents it "
                      "names, never the author's conversation; or a person other than the engineer who ran the session",
                      " ".join(record.split()))
        self.assertRegex(record, r"DECISION  \{\{approve [^}]*\}\} at \{\{commit\}\}")

    def test_verify_reads_the_evidence_and_gives_no_verdict(self):
        self.assertIn("from the evidence file `plans/<KEY>/review-evidence.md` when its HEAD and the commit the trusted "
                      "run tested differ in no path outside `plans/<KEY>/`", skill("aidlc-verify"))
        table = read("skills/aidlc-verify/assets/evidence-table.md")
        self.assertIn("This is evidence, not a verdict", " ".join(table.split()))
        for row in ("test files changed:", "test count:"):
            self.assertIn(row, table, row)

    def test_the_evidence_cannot_be_empty_without_warning(self):
        text = flat(EVIDENCE)
        self.assertIn("Quote every pathspec pattern", text)
        self.assertIn("`':(top)*_test.go'`", text)
        self.assertIn("compares `<base>` with HEAD, never the working tree", text)
        self.assertIn("only from a clean tree (`git status --porcelain` prints nothing)", text)
        self.assertIn("git diff -U0 --no-renames <base> HEAD -- ':(top)' ':(top,exclude)plans/<KEY>/'", text)
        self.assertIn("git diff <base> HEAD -- ':(top)<check configuration path>'", text)
        for marker in ("xit(", "xdescribe(", "@Ignore", "@SuppressWarnings", "#[ignore]", "<NoWarn>"):
            self.assertIn(marker, text, marker)
        tests = flat("agents/reviewer-tests.md")
        self.assertIn("any test-looking path in Changed files that is not in Test files is a high finding", tests)
        self.assertIn("src/foo.test.ts", tests)
        self.assertIn("no loosened check configuration", flat("agents/reviewer-compliance.md"))
        for rel in ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md"):
            self.assertIn("quote each pattern", flat(rel).split("## Where to look", 1)[1], rel)

    def test_the_commands_cover_the_whole_repository_and_show_deletions(self):
        text = flat(EVIDENCE)
        self.assertNotIn("-- . ':(", text)
        for command in ("git diff --stat --no-renames <base> HEAD", "git diff --name-only --no-renames <base> HEAD",
                        "git diff --no-renames <base> HEAD -- ':(top)<test path>'"):
            self.assertIn(command, text, command)
        for name in ("aidlc-build", "aidlc-verify", "aidlc-review"):
            self.assertIn("':(top)' ':(top,exclude)plans/<KEY>/'", section(skill(name), "## Rules"), name)
        self.assertIn("':(top)' ':(top,exclude)plans/<KEY>/'", section(skill("aidlc-review"), "## Stop if"))

    def test_the_adr_says_the_session_writes_the_evidence(self):
        consequences = flat("docs/adr/0024-instructions-first.md").split("## Consequences", 1)[1]
        self.assertIn("The session writes the evidence file the reviewers read, so the evidence is only as honest as "
                      "that session", consequences)


class BuildAndPlanTest(unittest.TestCase):
    """Task 3: the build and the plan name no script. The recipe check is a git procedure, a person starts each
    delegate slice, and the plan check is the plan's checklist."""

    def test_the_recipe_check_is_done_with_git(self):
        build = skill("aidlc-build")
        for phrase in ("`git worktree add <folder> <commit>^`", "`git -C <folder> add -A`",
                       "`git -C <folder> diff --cached --stat <commit>` must print nothing",
                       "the test count must be the same at the parent and at the commit"):
            self.assertIn(phrase, build, phrase)
        self.assertNotIn("check_recipe_commit", build)
        self.assertIn("the evidence file's Recipe commits section shows the re-run", flat("agents/reviewer-compliance.md"))
        self.assertNotIn("recipe check output", read("skills/aidlc-review/assets/pr-description.md"))

    def test_a_person_starts_each_delegate_slice(self):
        build = skill("aidlc-build")
        self.assertNotIn("slice runner", build)
        self.assertIn("one fresh session per slice, each started by the person", build)
        self.assertNotIn("slice runner", read("skills/aidlc-build/assets/progress-note.md"))

    def test_the_plan_check_is_a_checklist(self):
        plan = skill("aidlc-plan")
        self.assertNotIn("plan check", plan)
        self.assertIn("go through the plan's checklist (`assets/plan.md`) item by item, against the files", plan)
        checklist = flat("skills/aidlc-plan/assets/plan.md")
        for item in ('every bundle field filled, or "none"', "each MODE allowed at its TIER",
                     "a part of a story across several repositories is at Tier 2 or above (ADR 0021)",
                     "every PINS line names the spec's current version",
                     "every criterion and edge case in the spec maps to a test here and to a slice's bundle"):
            self.assertIn(item, checklist, item)

    def test_slice_0_names_no_starter_workflow_or_script(self):
        plan = skill("aidlc-plan")
        self.assertNotIn("ai-review.yml", plan)
        self.assertNotIn("the check scripts", plan)
        self.assertNotIn("story status command", plan)
        self.assertIn("the team's CI configuration (`.github/workflows/ci.yml` on GitHub, `.gitlab-ci.yml` on GitLab)", plan)


    def test_the_recipe_result_reaches_the_evidence_file(self):
        build = skill("aidlc-build")
        step5 = build.split("5. **When the bundle has a RECIPE", 1)[1].split("\n6.", 1)[0]
        self.assertIn("Recipe commits section of the evidence file", " ".join(step5.split()))
        self.assertIn("the test count must be the same at the parent and at the commit; record both counts",
                      " ".join(step5.split()))
        step9 = build.split("9. Check the boundary", 1)[1].split("\n10.", 1)[0]
        self.assertIn("Recipe commits section", step9)
        self.assertIn("git status --porcelain", build.split("5. **When", 1)[0])
        for rel in ("skills/aidlc-build/assets/review-evidence.md", "skills/aidlc-review/assets/review-evidence.md"):
            recipe = flat(rel).split("## Recipe commits", 1)[1]
            self.assertIn("git diff <commit>^ <commit> -- ':(top)<test path>'", recipe, rel)

    def test_the_plan_checklist_covers_the_plans_own_fields(self):
        self.assertIn("the plan's own fields (SPEC, APPROACH, FILES, TESTS, ORDER, RISKS, ROLLBACK, OPEN) are filled",
                      flat("skills/aidlc-plan/assets/plan.md"))


class StoryLevelTest(unittest.TestCase):
    """Task 4: a story's status and its release come from git and a person's confirmation; the contract checks are
    commands the team runs in its own CI."""

    FILES = ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/story-index.md",
             "skills/aidlc-plan/assets/criteria.md", "skills/aidlc-design/assets/coordination-plan.md",
             "starter/workspace/stories/README.md", "starter/workspace/WORKSPACE.md",
             "skills/aidlc-onboard/assets/workspace.md", "skills/aidlc-specify/SKILL.md",
             "skills/aidlc-design/SKILL.md", "skills/aidlc-release/SKILL.md", "skills/designing-apis/SKILL.md",
             "docs/operating-model/routes.md", "docs/operating-model/workspace-and-repositories.md")

    def test_no_story_level_file_names_the_status_or_contract_scripts(self):
        for rel in self.FILES:
            text = flat(rel)
            for name in ("story_status", "story status command", "status script", "check_contract_",
                         "contract pin command", "contract-publish.yml", "contract-check", "--check-release"):
                self.assertNotIn(name, text, f"{rel}: {name}")

    def test_status_is_derived_from_git(self):
        for rel in ("starter/workspace/WORKSPACE.md", "skills/aidlc-onboard/assets/workspace.md"):
            text = flat(rel)
            self.assertIn("`git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`", text, rel)
            self.assertIn("Nobody edits that file by hand.", text, rel)
            self.assertIn("a person adds or removes the repository's line in the root's `.gitignore`", text, rel)
        self.assertIn("the AI at the workspace root reads each part's index on its repository's default branch with git",
                      flat("skills/aidlc-design/assets/coordination-plan.md"))

    def test_release_fills_one_row_per_part_and_a_person_confirms(self):
        release = skill("aidlc-release")
        for phrase in ("fill the Parts table in `assets/readiness.md`", "The person confirms each row.",
                       "`git merge-base --is-ancestor <commit> origin/<default branch>`",
                       "The table is the release check. Any mismatch it reports blocks the release."):
            self.assertIn(phrase, release, phrase)
        readiness = read("skills/aidlc-release/assets/readiness.md")
        self.assertIn("## Parts (a story across several repositories)", readiness)
        self.assertEqual(readiness.count("- [ ] "), 10)

    def test_designing_apis_gives_the_contract_commands(self):
        text = flat("skills/designing-apis/SKILL.md")
        for command in ("oasdiff breaking <last copy> <path> --fail-on ERR --allow-external-refs=false",
                        "sha256sum -c -", "git ls-remote --tags <repository> 'refs/tags/api-v<version>'",
                        "git tag api-v<version> <merge commit>",
                        "git clone --depth 1 --branch api-v<version> <repository> <folder>"):
            self.assertIn(command, text, command)
        self.assertIn("with the commands in `designing-apis` (`sha256sum -c` against its SOURCE", skill("aidlc-release"))

    def test_commands_fetch_first_and_a_missing_result_stops(self):
        release = skill("aidlc-release")
        self.assertIn("run `git fetch` at the root, then check ancestry", release)
        self.assertIn("equals the story's CURRENT spec version, and the spec file's own version at that commit", release)
        self.assertIn("run `git -C <repository> fetch`, then read each part's PINS line", skill("aidlc-design"))
        apis = flat("skills/designing-apis/SKILL.md")
        for phrase in ("Empty output, an error, or a commit different from the one in `SOURCE` stops the release.",
                       "If there is no tag yet, this is the first publish: skip the oasdiff step and the version comparison",
                       "'refs/tags/api-v<version>' 'refs/tags/api-v<version>^{}'"):
            self.assertIn(phrase, apis, phrase)
        self.assertNotIn("api-v<version>*'", apis)
        self.assertIn("An unconfirmed row (a blank \"Confirmed by\") or a row that lists differing lines also blocks",
                      flat("skills/aidlc-release/assets/readiness.md"))


class OnboardTest(unittest.TestCase):
    """Task 5: onboarding copies no script and no workflow, and the rules file names no script."""

    GUIDES = ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md")

    def test_the_rules_file_names_no_script(self):
        for rel in self.GUIDES:
            text = flat(rel)
            for name in ("scripts/check_", "run_slices", "slice check", "Slice runner", "Plan check", "Recipe check,",
                         "Contract pin,"):
                self.assertNotIn(name, text, f"{rel}: {name}")
            for phrase in ("the commands from the `designing-apis` skill, or none",
                           "The compliance reviewer reports a new suppression or skip",
                           "recipe commit, re-run on its parent with git and compared (ADR 0012)"):
                self.assertIn(phrase, text, f"{rel}: {phrase}")

    def test_onboard_copies_no_script_or_workflow(self):
        onboard = skill("aidlc-onboard")
        for name in ("story_status", "check_slice", "check_plan", "check_recipe_commit", "run_slices",
                     "check_contract_", "ai-review.yml", "contract-check.yml", "contract-publish.yml",
                     "the starter's workflow", "--write-gitignore", "Ask the person to turn on branch protection"):
            self.assertNotIn(name, onboard, name)
        for phrase in ("aidlc ships no check of its own (ADR 0024)",
                       "Then write the root's `.gitignore`: one line per repository",
                       "the team may take the example settings",
                       "A team whose code host can require a code owner's review before a merge may turn that on; "
                       "aidlc never needs it.",
                       "propose the provider's checks from `designing-apis`"):
            self.assertIn(phrase, onboard, phrase)

    def test_the_suppression_reference_names_no_slice_check(self):
        text = flat("skills/aidlc-onboard/references/suppression-rules.md")
        self.assertNotIn("slice check", text)
        self.assertIn("the compliance reviewer reads each added one in the session's evidence file", text)
        self.assertIn("## Closing directives", read("skills/aidlc-onboard/references/suppression-rules.md"))

    def test_fix_round_1_says_what_optional_means_and_who_catches_a_breach(self):
        onboard = skill("aidlc-onboard")
        self.assertEqual(onboard.count("Without a required-checks or code-owner rule in the review tool, these checks are "
                                       "advice: a person can merge past them."), 2)
        self.assertIn("fill the `Where to look` lines the evidence file reads (test paths, dependency manifests, "
                      "check configuration)", onboard)
        for rel in self.GUIDES:
            self.assertIn("The compliance and test reviewers read the evidence file for these, and the code owner "
                          "approves", flat(rel), rel)


class FeedbackInStructureTest(unittest.TestCase):
    """Task 6: a repeated mistake becomes a check in the team's project, proven on the real past mistake, and a row in
    the rules table of the team's AGENTS.md."""

    def test_the_lesson_becomes_a_check_in_the_teams_project(self):
        feedback = skill("aidlc-feedback")
        for phrase in ("Encode each lesson in structure, in the team's project.", "aidlc ships none (ADR 0024)",
                       "A mistake that repeated (in two sessions, two reviews, or an incident) always gets a check above "
                       "layer 4.",
                       "run it on the commit that still holds the mistake (`git worktree add <folder> <commit>`",
                       "the commit of the past mistake it was seen failing on"):
            self.assertIn(phrase, feedback, phrase)
        self.assertIn("when a session repeats a mistake", section(feedback, "## When to use"))
        self.assertIn("A proposed check that lives outside the team's project", section(feedback, "## Red flags"))

    def test_the_rules_table_lives_in_the_teams_project(self):
        for rel in ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md"):
            text = flat(rel)
            self.assertIn("Every check named here lives in this repository", text, rel)
            self.assertIn("a check is listed only after it was seen failing on a real past mistake", text, rel)
            self.assertIn("with the failing run's command and output recorded in `feedback.md`", text, rel)

    def test_the_proof_fails_on_the_mistake_passes_on_the_fix_and_asks_before_a_new_tool(self):
        feedback = skill("aidlc-feedback")
        for phrase in ("copy the new check into that folder and see it fail there",
                       "then run it on the fixed code and see it pass",
                       "A check that fails in both places, or passes in both, is not proven.",
                       "A check that needs a new tool, lint plugin, dependency or CI step is proposed to its owner and "
                       "waits for the answer.",
                       "record the failing run's command and output in `feedback.md`"):
            self.assertIn(phrase, feedback, phrase)


RECORDING = ("aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-design", "aidlc-plan", "aidlc-build",
             "aidlc-verify", "aidlc-review", "aidlc-release", "aidlc-operate", "aidlc-feedback", "aidlc-onboard")
RULE = ("- People decide; you record the decision after checking it (ADR 0023). Accept a decision only from the decider "
        "in this session, or from a state you can check: a pull request approved in the review tool by a code owner who "
        "is not its author, the team's CI result on it, the merge state, or the tracker through its connected tool.")
GITHUB_ONLY = ("checked on GitHub", "approved on GitHub", "checking on GitHub", "state on GitHub", "on GitHub where",
               "in GitHub;", "on GitHub, is the record", "GitHub permalink", "PR #", "required check")


class HostNeutralTest(unittest.TestCase):
    """Task 7: aidlc needs git and a review request, and no feature of one code host."""

    def test_the_rules_bullet_is_host_neutral_and_identical(self):
        bullets = set()
        for name in RECORDING:
            rules = section(skill(name), "## Rules")
            bullet = rules[rules.index("- People decide;"):].split(" - ", 1)[0]
            bullets.add(bullet)
            self.assertTrue(bullet.startswith(RULE), name)
            self.assertNotIn("GitHub", bullet, name)
            self.assertIn("`approved by ana on pull request 12, checked in the review tool, 2026-11-20`", bullet, name)
        self.assertEqual(len(bullets), 1)

    def test_no_stage_skill_template_agent_or_doc_needs_a_github_feature(self):
        paths = (sorted((ROOT / "skills").glob("aidlc-*/SKILL.md")) + sorted((ROOT / "skills").glob("aidlc-*/assets/*.md"))
                 + sorted((ROOT / "agents").glob("*.md")) + sorted((ROOT / "docs/operating-model").glob("*.md")))
        for path in paths:
            text = " ".join(path.read_text(encoding="utf-8").split())
            for phrase in GITHUB_ONLY:
                self.assertNotIn(phrase, text, f"{path.relative_to(ROOT)}: {phrase}")
            for m in re.finditer(r"branch protection", text):
                self.assertIn("never needs it", text[m.start():m.start() + 120], f"{path.relative_to(ROOT)}")

    def test_pull_request_is_defined_once_and_change_request_stays_route_c(self):
        text = skill("using-aidlc")
        self.assertIn('A "pull request" is the code host\'s review request', text)
        self.assertIn('"Change request" is never a pull request', text)
        self.assertIn("| C · change request, story in progress |", read("skills/using-aidlc/SKILL.md"))

    def test_tracker_links_are_permalinks_on_any_code_host(self):
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/story-index.md"):
            self.assertIn("permalinks at a commit (the full commit hash in the address)", flat(rel), rel)
        self.assertIn("permalink at a commit: the file's address on the code host", skill("aidlc-start"))
        self.assertIn("Link the spec by its permalink at the commit where it merged", skill("aidlc-specify"))

    def test_the_ownership_list_goes_where_the_review_tool_reads_it(self):
        for rel in ("starter/repo/CODEOWNERS", "starter/workspace/CODEOWNERS"):
            self.assertIn("Put this file where your review tool reads it", flat(rel), rel)


class DocsTest(unittest.TestCase):
    """Task 8: the README, the docs, the map, the manifest and the change list say what is true today."""

    def test_the_readme_says_aidlc_is_instructions(self):
        readme = flat("README.md")
        gates = read("README.md").split("## Where the gates hold", 1)[1].split("\n## ", 1)[0]
        self.assertIn("It ships no scripts and no CI workflows (ADR 0024)", readme)
        self.assertIn("aidlc needs git and a pull request (a review request), and no other code-host feature", readme)
        for name in ("Slice check", "Stop hook", "AI review in CI", "check scripts"):
            self.assertNotIn(name, gates, name)
        self.assertNotIn("The skills work in **Claude Code, GitHub Copilot, Codex and Cursor**", read("README.md"))

    def test_the_manifest_claims_only_what_is_true(self):
        description = json.loads(read(".claude-plugin/plugin.json"))["description"]
        self.assertNotIn("the same skills work in", description)
        self.assertIn("Written and tested for Claude Code", description)

    def test_the_archive_note_says_where_the_code_went(self):
        note = flat("docs/archive/checks-v1.md")
        self.assertIn("git checkout checks-v1 -- <path>", note)
        for name in ("check_slice.py", "check_plan.py", "check_recipe_commit.py", "run_slices.py",
                     "check_contract_version.py", "check_contract_pin.py", "story_status.py", "ai-review.yml",
                     "contract-check.yml", "contract-publish.yml"):
            self.assertIn(name, note, name)
        self.assertIn("docs/archive/checks-v1.md", read("docs/codebase-map.md"))
        self.assertIn("no scripts and no workflows (ADR 0024)", flat("AGENTS.md"))

    def test_the_change_list_marks_what_plan_22_dropped(self):
        changes = read("docs/design/2026-11-19-aidlc-6-change-list.md")
        self.assertIn("Superseded in part by ADR 0024", changes)
        table = changes.split("## 6. After ADR 0024 (2026-11-20)", 1)[1]
        for item in ("A1", "C4", "F6", "F7", "F9", "E1", "G1", "B5", "C2"):
            self.assertRegex(table, rf"\b{item}\b", item)

    def test_the_quickstarts_and_adoption_copy_no_script_or_workflow(self):
        for rel in ("docs/quickstart/claude-code.md", "docs/quickstart/copilot.md", "docs/quickstart/codex-cursor.md"):
            text = flat(rel)
            self.assertNotIn("ci.yml", text, rel)
            self.assertNotIn("`scripts/`", text, rel)
        adoption = flat("docs/operating-model/adoption.md")
        for name in ("run_slices", "ai-review.yml"):
            self.assertNotIn(name, adoption, name)
        self.assertIn("`aidlc-feedback` turns it into a check in the team's own project", adoption)

    def test_the_eval_fixtures_name_no_removed_script(self):
        for rel in ("evals/fixtures/workspace/WORKSPACE.md", "evals/fixtures/workspace/stories/README.md"):
            self.assertNotIn("story_status.py", read(rel), rel)


REMOVED_NAMES = ("check_slice.py", "check_plan.py", "check_recipe_commit.py", "check_contract_version.py",
                 "check_contract_pin.py", "run_slices.py", "story_status.py", "ai-review.yml", "contract-check.yml",
                 "contract-publish.yml", "slice check", "plan check", "story status command", "slice runner",
                 "Stop hook", "contract pin command", "--write-gitignore", "--check-release")


def live_text_files() -> list[Path]:
    """The files a team reads or copies: skills, agents, starters, the operating model, the quickstarts, the README,
    AGENTS.md, CLAUDE.md and the plugin manifest. History (ADRs, designs, plans, verification records, the archive)
    and the eval fixtures are left out."""
    roots = [ROOT / "skills", ROOT / "agents", ROOT / "starter", ROOT / "docs/operating-model", ROOT / "docs/quickstart"]
    files = [p for r in roots for p in r.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return files + [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / ".claude-plugin/plugin.json"]


class NoShippedCodeTest(unittest.TestCase):
    """Task 9: the starters hold no script and no workflow; the example settings keep what protects secrets and the
    settings themselves; nothing a team reads names the removed code."""

    def test_the_starters_hold_no_script_and_no_workflow(self):
        for kind in ("repo", "workspace"):
            base = ROOT / "starter" / kind
            self.assertFalse((base / "scripts").exists(), kind)
            self.assertFalse((base / ".github").exists(), kind)
            self.assertEqual([p for p in base.rglob("*") if p.suffix in (".py", ".sh", ".yml", ".yaml")], [], kind)
        for name in ("test_check_slice.py", "test_check_plan.py", "test_check_recipe_commit.py",
                     "test_check_contract.py", "test_run_slices.py", "test_story_status.py"):
            self.assertFalse((ROOT / "scripts" / name).exists(), name)

    def test_the_example_settings_keep_the_secret_denies_and_drop_the_rest(self):
        for kind in ("repo", "workspace"):
            settings = json.loads(read(f"starter/{kind}/.claude/settings.json"))
            self.assertNotIn("hooks", settings, kind)
            deny = settings["permissions"]["deny"]
            for rule in ("Read(**/.env)", "Read(**/*.pem)", "Read(~/.ssh/**)", "Edit(/.claude/**)", "Edit(/CODEOWNERS)"):
                self.assertIn(rule, deny, f"{kind}: {rule}")
            self.assertEqual([r for r in deny if "scripts/" in r or "workflows/" in r], [], kind)
            self.assertTrue(settings["sandbox"]["enabled"], kind)
        ask = json.loads(read("starter/repo/.claude/settings.json"))["permissions"]["ask"]
        for rule in ("Bash(git push*)", "Bash(npm install*)", "Bash(pip install*)", "Bash(dotnet add package*)"):
            self.assertIn(rule, ask, rule)

    def test_no_file_a_team_reads_names_the_removed_code(self):
        hits = []
        for path in live_text_files():
            text = " ".join(path.read_text(encoding="utf-8").split())
            hits += [f"{path.relative_to(ROOT)}: {name}" for name in REMOVED_NAMES if name in text]
        self.assertEqual(hits, [])

    def test_the_owners_still_hold_the_teams_own_checks(self):
        owners = read("starter/repo/CODEOWNERS")
        for line in (r"(?m)^scripts/\s+@your-org/your-team-leads$", r"(?m)^\.github/\s+@your-org/your-team-leads$",
                     r"(?m)^\.claude/\s+@your-org/your-team-leads$", r"(?m)^CLAUDE\.md\s+@your-org/your-team-leads$",
                     r"(?m)^\.mcp\.json\s+@your-org/your-team-leads$"):
            self.assertRegex(owners, line)
        for rel in ("starter/repo/CODEOWNERS", "starter/workspace/CODEOWNERS"):
            self.assertIn("aidlc ships none", read(rel), rel)


class RecordTest(unittest.TestCase):
    """Task 10: the plan is recorded."""

    def test_the_verification_record_exists(self):
        record = read("docs/verification/2026-11-20-plan-22.md")
        for heading in ("## What changed", "## How it was checked", "## Evidence", "## Not verified here",
                        "## For the owner"):
            self.assertIn(heading, record, heading)
        for phrase in ("checks-v1", "ADR 0024", "python3 scripts/validate.py", "claude plugin validate ."):
            self.assertIn(phrase, record, phrase)

    def test_the_record_has_no_open_slot(self):
        self.assertNotIn("{{", read("docs/verification/2026-11-20-plan-22.md"))

    def test_the_evidence_file_has_nine_section_headings(self):
        for rel in ("skills/aidlc-build/assets/review-evidence.md", "skills/aidlc-review/assets/review-evidence.md"):
            self.assertEqual(len(re.findall(r"(?m)^## ", read(rel))), 9, rel)


EVIDENCE_COPIES = ("skills/aidlc-build/assets/review-evidence.md", "skills/aidlc-review/assets/review-evidence.md")
TOP_RULE = "Run every command from the repository root (`cd \"$(git rev-parse --show-toplevel)\"`)"


def clean_env() -> dict:
    """The environment with every GIT_ variable removed, so a throwaway repository never reaches an outer one, and
    with no user or system configuration, so no global hook runs."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return dict(env, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
                GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def git(cwd: Path, *args: str) -> str:
    """Run git in a throwaway repository."""
    return subprocess.run(["git", *args], cwd=cwd, env=clean_env(), check=True, capture_output=True, text=True).stdout


class FinalReviewTest(unittest.TestCase):
    """The final review's fix wave: the evidence commands see the whole repository from any folder, the recipe check
    counts the parent's tests before the recipe runs, an approval a session cannot read is confirmed by a person, and
    the minor items."""

    def test_i1_every_evidence_command_runs_from_the_root_with_top_pathspecs(self):
        self.assertEqual(read(EVIDENCE_COPIES[0]), read(EVIDENCE_COPIES[1]))
        text = flat(EVIDENCE)
        self.assertIn(TOP_RULE, text)
        for command in ("git diff --no-renames <base> HEAD -- ':(top)<test path>'",
                        "git diff <base> HEAD -- ':(top)<manifest>'",
                        "git diff <base> HEAD -- ':(top)<check configuration path>'",
                        "git diff <base> HEAD -- ':(top)plans/<KEY>/'",
                        "git diff <commit>^ <commit> -- ':(top)<test path>'"):
            self.assertIn(command, text, command)
        self.assertNotRegex(text, r"-- '<|-- plans/")
        step5 = skill("aidlc-build").split("5. **When the bundle has a RECIPE", 1)[1].split(" 6. ", 1)[0]
        self.assertIn("git diff <commit>^ <commit> -- ':(top)<test path>'", step5)
        self.assertIn("`cd \"$(git rev-parse --show-toplevel)\"`", step5)
        self.assertNotIn("-- '<test paths>'", step5)

    def test_i1_the_test_file_command_sees_every_change_from_a_subfolder(self):
        section_text = flat(EVIDENCE).split("## Test files", 1)[1].split(" ## ", 1)[0]
        command = re.search(r"`(git diff --no-renames <base> HEAD -- [^`]+)`", section_text).group(1)
        command = command.replace("':(top)<test path>'", "':(top)tests/' ':(top)*_test.go'")
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            git(repo, "init", "-q")
            for rel, body in (("tests/test_orders.py", "def test_total():\n    assert total == 120\n"),
                              ("src/billing/invoice_test.go", "package billing\n"),
                              ("src/api/handler.go", "package api\n")):
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text(body, encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            base = git(repo, "rev-parse", "HEAD").strip()
            (repo / "src/billing/invoice_test.go").unlink()
            (repo / "tests/test_orders.py").write_text("def test_total():\n    assert total > 0\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "weaken")
            command = command.replace("<base>", base)
            self.assertNotIn("<", command)
            out = subprocess.run(command, shell=True, cwd=repo / "src/api", env=clean_env(), check=True,
                                 capture_output=True, text=True).stdout
        self.assertIn("deleted file mode", out)
        self.assertIn("src/billing/invoice_test.go", out)
        self.assertIn("-    assert total == 120", out)
        self.assertIn("+    assert total > 0", out)

    def test_i2_the_parents_count_comes_before_the_recipe_runs(self):
        for rel in EVIDENCE_COPIES:
            recipe = flat(rel).split("## Recipe commits", 1)[1].lower()
            order = [recipe.index(p.lower()) for p in ("run the test command there first, for the parent's count",
                                                       "run the bundle's RECIPE there", "`git -C <folder> add -A`",
                                                       "`git -C <folder> diff --cached --stat <commit>`",
                                                       "run the test command there again, for the commit's count")]
            self.assertEqual(order, sorted(order), rel)
            self.assertIn("because the recipe then changes the worktree", recipe, rel)
        step5 = skill("aidlc-build").split("5. **When the bundle has a RECIPE", 1)[1].split(" 6. ", 1)[0]
        lowered = step5.lower()
        order = [lowered.index(p.lower()) for p in ("run the repository's test command (named in `AGENTS.md`) there "
                                                    "first, for the parent's count", "run the approved command",
                                                    "`git -C <folder> add -A`",
                                                    "`git -C <folder> diff --cached --stat <commit>`",
                                                    "run the test command again, for the commit's count")]
        self.assertEqual(order, sorted(order))
        self.assertIn("because the recipe then changes the worktree", step5)

    def test_i3_an_approval_the_session_cannot_read_is_confirmed_by_the_code_owner(self):
        step8 = skill("aidlc-review").split(" 8. Mark this stage's row", 1)[1].split("## Produces", 1)[0]
        self.assertIn("When you cannot read the review tool, the code owner confirms the approval and the CI result in "
                      "this session, and the record says so (`confirmed by <name> in the session, <date>`); otherwise "
                      "leave the row and report.", step8)
        claim = "aidlc needs git and a pull request (a review request), and no other code-host feature"
        optional = "Reading the review tool is optional: without it, a person confirms"
        for text in (skill("using-aidlc"), flat("README.md")):
            self.assertIn(claim, text)
            self.assertIn(optional, text)
        description = json.loads(read(".claude-plugin/plugin.json"))["description"]
        self.assertIn("needs git and a pull request, and no other code-host feature", description)
        self.assertNotIn("no code-host feature needed", description)

    def test_m4_the_story_documents_diff_leaves_out_the_evidence_file(self):
        for rel in EVIDENCE_COPIES:
            story = flat(rel).split("## Story documents", 1)[1].split(" ## ", 1)[0]
            self.assertIn("':(top,exclude)plans/<KEY>/review-evidence.md'", story, rel)
            self.assertIn("':(top,exclude)plans/<KEY>/part-<n>/review-evidence.md'", story, rel)

    def test_m5_the_build_may_edit_the_evidence_file(self):
        rule = section(skill("aidlc-build"), "## Rules").split("- You edit only inside MAY CHANGE.", 1)[1]
        self.assertIn("Of the `plans/` documents, edit only your progress note and your row in the index, plus the "
                      "evidence file (`plans/<KEY>/review-evidence.md`, or `plans/<KEY>/part-<n>/review-evidence.md` "
                      "for a second part), which step 9 writes.", rule)

    def test_m6_verify_uses_the_evidence_file_by_the_void_rule(self):
        verify = skill("aidlc-verify")
        self.assertNotIn("when its HEAD is the commit the trusted run tested", verify)
        self.assertIn("when its HEAD and the commit the trusted run tested differ in no path outside `plans/<KEY>/` "
                      "(`git diff --name-only <evidence HEAD> <tested commit> -- ':(top)' ':(top,exclude)plans/<KEY>/'` "
                      "prints nothing, the same command as the verdict rule)", verify)

    def test_m7_the_recipe_row_names_where_the_rule_lives(self):
        for rel in ("docs/adr/0024-instructions-first.md", "docs/design/2026-11-20-instructions-first.md"):
            row = [line for line in read(rel).splitlines() if line.startswith("| Recipe commit is mechanical")][0]
            self.assertNotIn("DONE WHEN", row, rel)
            self.assertIn("`aidlc-build` step 5 and the evidence file's Recipe commits section", row, rel)

    def test_m8_adr_0019_names_a_proposed_replacement(self):
        self.assertIn("Status: Superseded by ADR 0024 (proposed, 2026-11-20)",
                      read("docs/adr/0019-gates-enforced-by-code.md"))

    def test_m9_the_reviewers_know_the_second_part_path(self):
        for name in ("reviewer-tests", "reviewer-compliance"):
            self.assertIn("`plans/<KEY>/part-<n>/review-evidence.md` for a second part", flat(f"agents/{name}.md"), name)

    def test_m10_specify_checks_the_parts_itself(self):
        specify = skill("aidlc-specify")
        self.assertNotIn("the next `status.md` the AI derives", specify)
        self.assertIn("run `git -C <repository> fetch`, then read the part's PINS line on its default branch, with "
                      "`git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`", specify)

    def test_m11_the_base_is_read_after_a_fetch(self):
        for rel in EVIDENCE_COPIES:
            self.assertIn("{{git fetch, then git merge-base HEAD origin/<default branch>}}", read(rel), rel)

    def test_m12_the_archive_note_tells_5x_teams_how_to_upgrade(self):
        note = flat("docs/archive/checks-v1.md")
        self.assertIn("## Upgrading a repository onboarded on 5.x", read("docs/archive/checks-v1.md"))
        self.assertIn("run `aidlc-onboard` again to add the \"Where to look\" lines the evidence file reads", note)
        self.assertIn("The scripts and workflows you copied are yours to keep or delete", note)

    def test_m13_the_verdict_bullet_names_what_reviewers_are_given(self):
        self.assertIn("dispatched with the evidence file and the story documents it names, never the author's "
                      "conversation", VERDICT)
        self.assertNotIn("dispatched with only", flat("skills/aidlc-review/assets/review-record.md"))
        for name in ("aidlc-build", "aidlc-verify", "aidlc-review"):
            self.assertNotIn("dispatched with only", skill(name), name)

    def test_m14_the_change_list_states_the_version(self):
        changes = read("docs/design/2026-11-19-aidlc-6-change-list.md")
        self.assertNotIn("Needs the owner's decision", changes)
        self.assertNotIn("rises to 6.0.0 when phases 1 and 2 land", changes)
        self.assertIn("6.0.0 (approved 2026-11-20)", changes)
        table = changes.split("## 6. After ADR 0024 (2026-11-20)", 1)[1]
        self.assertIn("items D1–D3", table)
        self.assertIn("(item D2 without `run_slices.py`)", table)

    def test_m15_the_copilot_cli_install_is_marked_untested(self):
        self.assertIn("install the plugin with Copilot CLI (untested)", read("README.md"))
        self.assertIn("(untested)", flat("docs/quickstart/copilot.md").split("Copilot CLI and the cloud agent", 1)[1][:200])

    def test_m16_the_record_counts_the_fix_rounds_and_the_final_review(self):
        record = flat("docs/verification/2026-11-20-plan-22.md")
        self.assertNotIn("9 in Task 9 alone", record)
        self.assertIn("9 from the fix rounds of Tasks 1 to 8", record)
        self.assertIn("## Final review", read("docs/verification/2026-11-20-plan-22.md"))
        self.assertNotIn("Final review: not done yet", record)
        self.assertNotIn("The final whole-branch review and its fix wave are still to come", record)


if __name__ == "__main__":
    unittest.main()
