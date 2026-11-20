"""Plan 22: aidlc is instructions (ADR 0024). It ships no scripts and no CI workflows; the checks live in the
team's project; a verdict counts only from someone who did not write the change, at a named commit; and the words
need git, not a code host's features."""
import json
import re
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
        self.assertIn("Status: Superseded by ADR 0024 (2026-11-20)", read("docs/adr/0019-gates-enforced-by-code.md"))

    def test_each_amended_adr_carries_a_dated_note(self):
        for name in AMENDED:
            text = read(f"docs/adr/{name}.md")
            self.assertIn("Amended by ADR 0024 (2026-11-20): see the last section.", text, name)
            self.assertTrue(text.rstrip().split("\n## ")[-1].startswith("Amended by ADR 0024 (2026-11-20)"), name)
            self.assertIn("Status: Accepted", text, name)


VERDICT = ("- A verdict that the change is done or passes counts only from someone who did not write it: one of the "
           "`reviewer-*` agents, dispatched with only the evidence file, the bundle and the diff, or a person other "
           "than the engineer who ran the session. It names the commit it judged (`git rev-parse HEAD`). A later "
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
                        "git diff --name-only --no-renames <base> HEAD", "git diff --no-renames <base> HEAD -- '<test paths>'",
                        "git diff <base> HEAD -- '<manifests>'", "git diff <base> HEAD -- plans/<KEY>/",
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
        self.assertIn("one of the `reviewer-*` agents, dispatched with only the evidence file, the bundle and the "
                      "diff, or a person other than the engineer who ran the session", " ".join(record.split()))
        self.assertRegex(record, r"DECISION  \{\{approve [^}]*\}\} at \{\{commit\}\}")

    def test_verify_reads_the_evidence_and_gives_no_verdict(self):
        self.assertIn("from the evidence file `plans/<KEY>/review-evidence.md` when its HEAD is the commit the trusted "
                      "run tested", skill("aidlc-verify"))
        table = read("skills/aidlc-verify/assets/evidence-table.md")
        self.assertIn("This is evidence, not a verdict", " ".join(table.split()))
        for row in ("test files changed:", "test count:"):
            self.assertIn(row, table, row)

    def test_the_evidence_cannot_be_empty_without_warning(self):
        text = flat(EVIDENCE)
        self.assertIn("Quote every pathspec pattern", text)
        self.assertIn("`'*_test.go'`", text)
        self.assertIn("compares `<base>` with HEAD, never the working tree", text)
        self.assertIn("only from a clean tree (`git status --porcelain` prints nothing)", text)
        self.assertIn("git diff -U0 --no-renames <base> HEAD -- ':(top)' ':(top,exclude)plans/<KEY>/'", text)
        self.assertIn("git diff <base> HEAD -- '<check configuration>'", text)
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
                        "git diff --no-renames <base> HEAD -- '<test paths>'"):
            self.assertIn(command, text, command)
        for name in ("aidlc-build", "aidlc-verify", "aidlc-review"):
            self.assertIn("':(top)' ':(top,exclude)plans/<KEY>/'", section(skill(name), "## Rules"), name)
        self.assertIn("':(top)' ':(top,exclude)plans/<KEY>/'", section(skill("aidlc-review"), "## Stop if"))

    def test_the_adr_says_the_session_writes_the_evidence(self):
        consequences = flat("docs/adr/0024-instructions-first.md").split("## Consequences", 1)[1]
        self.assertIn("The session writes the evidence file the reviewers read, so the evidence is only as honest as "
                      "that session", consequences)


if __name__ == "__main__":
    unittest.main()
