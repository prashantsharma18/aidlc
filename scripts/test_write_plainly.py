"""Plan 29: write plainly. Five practices adapted from pstack, keeping pstack's names, and the lines that call them."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRACTICE_SECTIONS = ("## When to use", "## Steps", "## Checks", "## Stop if", "## Common excuses", "## Red flags",
                     "## Rules")
NEVER = ("Never change code, commands, file paths, identifiers, quoted text, test output, a template's fixed lines "
         "or a line another skill reads by its exact words (an index row, a FIELD line, a status word, a commit "
         "trailer): leave them byte for byte.")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def skill_md(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def skill(name: str) -> str:
    files = sorted((ROOT / "skills" / name / "references").glob("*.md"))
    return " ".join([flat(skill_md(name))] + [flat(p.read_text(encoding="utf-8")) for p in files])


def section(text: str, heading: str) -> str:
    return flat(text).split(heading, 1)[1].split(" ## ", 1)[0]


def front(name: str) -> str:
    return skill_md(name).split("\n---", 1)[0]


class PracticeShape:
    """Mixed into each task's test: a pstack practice with aidlc's practice sections."""
    NAME = ""
    SOURCE = ""

    def test_it_is_a_practice_the_model_can_load(self):
        head = front(self.NAME)
        self.assertIn(f"name: {self.NAME}", head)
        self.assertIn("  kind: practice", head)
        self.assertIn("  invocation: auto", head)
        self.assertNotIn("disable-model-invocation", head)
        self.assertIn("Use when", head)
        text = skill_md(self.NAME)
        for heading in PRACTICE_SECTIONS:
            self.assertIn("\n" + heading + "\n", text, heading)
        self.assertTrue(text.rstrip().endswith("- You draft; you never approve."))

    def test_it_credits_pstack(self):
        self.assertIn(f"Adapted from pstack's `{self.SOURCE}` (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan); "
                      "its notice is in `skills/NOTICE`.", flat(skill_md(self.NAME)))
        self.assertIn(f"`{self.NAME}`", flat(read("skills/NOTICE")))

    def test_it_is_named_where_a_team_reads(self):
        self.assertIn(f"`{self.NAME}`", section(skill_md("using-aidlc"), "## The practice map"))
        cell = next(line for line in read("README.md").splitlines() if line.startswith("| `aidlc-start`"))
        self.assertIn(f"`{self.NAME}`", cell.split("|")[2])
        self.assertIn(self.NAME, json.loads(read("scripts/routing_cases.json")))

    def test_it_is_never_a_gate(self):
        self.assertIn("None of its own: this skill never stops a stage.", section(skill_md(self.NAME), "## Stop if"))


class UnslopTest(PracticeShape, unittest.TestCase):
    """Task 1: `unslop`, the base layer."""
    NAME, SOURCE = "unslop", "unslop"

    def test_the_catalog_keeps_pstacks_numbers(self):
        catalog = read("skills/unslop/references/ai-tells.md")
        numbers = [int(n) for n in re.findall(r"(?m)^(\d+)\. ", catalog)]
        self.assertEqual(numbers, [3, 5] + list(range(7, 21)) + list(range(22, 34)))
        self.assertIn("Rule numbers are stable ids that other skills cite. A removed rule leaves a gap; a new rule "
                      "takes the next number.", flat(catalog))
        self.assertIn("13. No em dashes, en dashes, or hyphens used as dashes", catalog)
        self.assertIn("`references/ai-tells.md`", section(skill_md("unslop"), "## Steps"))

    def test_it_never_changes_technical_text_and_calls_no_skill(self):
        self.assertIn(NEVER, section(skill_md("unslop"), "## Steps"))
        self.assertNotRegex(skill("unslop"), r"[Ll]oad the `[a-z0-9-]+` skill")


class TechnicalWritingTest(PracticeShape, unittest.TestCase):
    """Task 1: `technical-writing`, the sentences; its last pass is `unslop`."""
    NAME, SOURCE = "technical-writing", "technical-writing"

    def test_its_steps(self):
        steps = section(skill_md("technical-writing"), "## Steps")
        self.assertIn(NEVER, steps)
        self.assertIn("`references/sentences.md`", steps)
        self.assertIn("A pull request description or a commit body is a briefing a reviewer reads in under a minute: "
                      "link logs, run histories and long tables, never paste them.", steps)
        self.assertTrue(steps.rstrip().endswith("Load the `unslop` skill as the last pass."))
        sentences = flat(read("skills/technical-writing/references/sentences.md"))
        for heading in ("Write so a tired engineer understands on the first read.", "## Vary the rhythm",
                        "## Write sentences to the reader (Google developer style)",
                        "## Make statements load one at a time (STE rules)",
                        "## Leave no sentence open to two readings (Global English)"):
            self.assertIn(heading, sentences, heading)
        self.assertIn("A table the document's template asks for stays in it.", steps)
        self.assertNotIn("Diátaxis", sentences)
        self.assertNotIn("Indent code snippets with tabs", sentences)

    def test_the_naming_rule(self):
        self.assertIn("A practice adapted from pstack keeps pstack's name (`unslop`, `technical-writing`, "
                      "`in-your-own-words`, `how`, `why`).", flat(read("docs/codebase-map.md")))


class InYourOwnWordsTest(PracticeShape, unittest.TestCase):
    """Task 2: restate a request before work starts."""
    NAME, SOURCE = "in-your-own-words", "in-your-own-words"

    def test_its_steps(self):
        steps = section(skill_md(self.NAME), "## Steps")
        for phrase in ("Restate the goal in your own words: what the person wants to be true when this is done, and "
                       "for whom.",
                       "Restate the problem: what is wrong now, and why it matters now.",
                       "Name each thing you assumed, as an assumption.",
                       "Ask the person to correct it. Their correction, not your restatement, is what the work starts "
                       "from."):
            self.assertIn(phrase, steps, phrase)
        self.assertIn("When the calling step goes on without waiting (a restatement that is not a stop, or a sub-agent), "
                      "state it and go on.", flat(steps))
        self.assertIn("The stages' restatements of a story (`aidlc-plan` step 1, `aidlc-build` step 2) stay their "
                      "own.", flat(skill_md(self.NAME)))

    def test_it_applies_where_stress_testing_decisions_loads_it(self):
        text = flat(skill_md(self.NAME))
        self.assertIn("Not for: restating a story's outcome and criteria.", text)
        self.assertNotIn("a story that already has its outcome and criteria", text)
        self.assertIn("Another skill restates a goal with it: `aidlc-intent` for a request, "
                      "`stress-testing-decisions` for the goal a decision serves.",
                      section(skill_md(self.NAME), "## When to use"))


class HowTest(PracticeShape, unittest.TestCase):
    """Task 2: how code works now."""
    NAME, SOURCE = "how", "how"

    def test_its_steps(self):
        steps = section(skill_md(self.NAME), "## Steps")
        for phrase in ("State your reading of the question in one sentence; the person may redirect it.",
                       "Brief the `explorer` agent with that one question, where your AI tool can start it; otherwise "
                       "explore read-only yourself, the same way.",
                       "present it as a mental model a senior engineer new to the area can work from",
                       "Mark what the code alone does not show as UNKNOWN."):
            self.assertIn(phrase, steps, phrase)
        self.assertIn("Use `why`", front(self.NAME))


class WhyTest(PracticeShape, unittest.TestCase):
    """Task 2: why it is like this, from the record."""
    NAME, SOURCE = "why", "why"

    def test_its_steps(self):
        steps = section(skill_md(self.NAME), "## Steps")
        for phrase in ("`git log --follow`", "`git blame`", "`git log -S",
                       "Answer from what the authors wrote, and cite each commit or pull request you use.",
                       "Mark every inference as INFERENCE, and say what the record does not answer."):
            self.assertIn(phrase, steps, phrase)
        self.assertIn("Use `how`", front(self.NAME))
        self.assertIn("a failing test or a broken build (`debugging-failures`)", flat(skill_md(self.NAME)))


STANDING = ("Apply the `unslop` skill to every reply a person reads, and the `technical-writing` skill to every "
            "document, pull request description and commit body.")
STAGE_LOADS = {
    "aidlc-intent": ("Load the `in-your-own-words` skill for each restatement this stage makes.",
                     "Load the `technical-writing` skill for its sentences."),
    "aidlc-specify": ("Load the `technical-writing` skill for the spec's sentences.",),
    "aidlc-design": ("Load the `technical-writing` skill for the ADR's and the design note's sentences.",),
    "aidlc-plan": ("Load the `technical-writing` skill.",),
    "aidlc-review": ("Load the `technical-writing` skill for the description's sentences.",),
    "aidlc-release": ("Load the `technical-writing` skill for the readiness checklist's and the change record's sentences.",),
    "aidlc-operate": ("Load the `technical-writing` skill for this record and for the work item in step 6.",),
    "aidlc-discover": ("To explain how a traced path works, load the `how` skill; to explain why it is like this, "
                       "load the `why` skill.",),
}


class CallersTest(unittest.TestCase):
    """Task 3: the other skills reach `unslop` as pstack does; the stages load at the moments a person decides."""

    def test_the_standing_rule(self):
        self.assertIn("- " + STANDING, section(skill_md("story-run"), "## Rules"))
        self.assertIn("- " + STANDING, flat(read("skills/lane-run/references/worker.md")))

    def test_the_last_pass_lines(self):
        self.assertIn("Load the `unslop` skill as the last pass on every document you wrote.",
                      section(skill_md("writing-documentation"), "## Steps"))
        self.assertIn("pick the document's mode and keep to it (Diátaxis)",
                      section(skill_md("writing-documentation"), "## Steps").split(" 2. ", 1)[0])
        self.assertIn("Load the `unslop` skill as the last pass on the body and on any pull request text you write.",
                      section(skill_md("committing-changes"), "## Steps"))
        step5 = flat(skill_md("reviewing-code")).split("### Step 5: Categorize Findings", 1)[1].split("## Dead Code", 1)[0]
        self.assertTrue(step5.strip().endswith("the structural problem *is* the review. Load the `unslop` skill as the "
                                               "last pass on the findings a person reads."))
        self.assertNotIn("optional suggestions. Load", skill_md("reviewing-code"))
        self.assertIn("1. Load the `in-your-own-words` skill for each restatement this stage makes. When the request is "
                      "vague", section(skill_md("aidlc-intent"), "## Steps"))
        self.assertIn("1. Load the `in-your-own-words` skill and restate the goal the decision serves. Write the "
                      "decision in one paragraph", section(skill_md("stress-testing-decisions"), "## Steps"))

    def test_the_stage_loads(self):
        for stage, lines in STAGE_LOADS.items():
            steps = section(skill_md(stage), "## Steps")
            for line in lines:
                self.assertIn(line, steps, (stage, line))
        for stage in ("aidlc-build", "aidlc-verify"):
            self.assertNotIn("`technical-writing`", skill_md(stage), stage)

    def test_the_playbooks_name_them_without_loading(self):
        bug = flat(read("skills/story-run/references/playbook-bug-fix.md"))
        self.assertIn("`debugging-failures`, for steps 1 to 3 (brief mode names it for a fix brief too); `why`, for "
                      "the history of the code the fix touches.", bug)
        inv = flat(read("skills/story-run/references/playbook-investigation.md"))
        self.assertIn("Write the finding through `unslop`, and answer a \"why\" from the record, as `why` says.", inv)
        for text in (bug, inv):
            self.assertNotRegex(text, r"[Ll]oad the `[a-z0-9-]+` skill")

    def test_the_map_says_who_loads_them(self):
        self.assertIn("`technical-writing` loads at each stage step that writes a document a person decides from, "
                      "and `unslop` is the last pass of every skill that writes prose", flat(skill_md("using-aidlc")))


class FrontMatterTest(unittest.TestCase):
    """Fix round 1: a plain YAML scalar must not hold ": " or " #"."""

    def test_plain_descriptions_are_valid_yaml_scalars(self):
        import glob
        import os
        for path in sorted(glob.glob(os.path.join(str(ROOT), "skills", "*", "SKILL.md"))):
            for line in open(path, encoding="utf-8").read().split("---")[1].splitlines():
                if line.startswith("description:"):
                    value = line[len("description:"):].strip()
                    if value.startswith(('"', "'")):
                        continue
                    self.assertNotIn(": ", value, path)
                    self.assertNotIn(" #", value, path)


class EvalCasesTest(unittest.TestCase):
    """Task 4: two cases for Plan 29, written and checked, not run."""

    def grader(self, case: str, name: str) -> str:
        return read(f"evals/{case}/graders/{name}")

    def test_the_cases(self):
        self.assertEqual(sorted(p.name for p in (ROOT / "evals/routing-unslop/graders").glob("*.md")),
                         ["fired.md", "keeps-command.md", "keeps-path.md", "no-ai-words.md", "no-dash.md"])
        self.assertEqual(sorted(p.name for p in (ROOT / "evals/routing-why-history/graders").glob("*.md")),
                         ["cites-contract.md", "fired.md", "read-history.md", "reply.md"])
        prompt = read("evals/routing-unslop/prompt.md")
        self.assertIn("kubectl rollout undo deployment/eta-api --namespace shipments", prompt)
        self.assertIn("\u2014", prompt)
        self.assertIn("scaffold_script: setup.sh", read("evals/routing-why-history/case.yaml"))
        self.assertIn("The two cases for Plan 29 are `routing-unslop` and `routing-why-history`, 53 in all",
                      read("evals/README.md"))

    def test_the_readme_says_a_regex_without_target_reads_the_final_reply(self):
        self.assertIn("a regex grader with no `target` reads the final reply (`last_message`)", flat(read("evals/README.md")))

    def test_the_graders_match_right_and_not_wrong(self):
        def pattern(case, name):
            front_matter = self.grader(case, name).split("---", 2)[1]
            line = next(l for l in front_matter.splitlines() if l.startswith(("pattern:", "input_match:")))
            return re.compile(line.split(":", 1)[1].strip()[1:-1])
        ai = pattern("routing-unslop", "no-ai-words.md")
        self.assertNotIn("flags", self.grader("routing-unslop", "no-ai-words.md").split("---", 2)[1])
        self.assertRegex("Delved into it", ai)
        self.assertRegex("a Pivotal step", ai)
        self.assertNotRegex("We looked into it", ai)
        self.assertNotRegex("an undelved pile", ai)
        cmd = pattern("routing-unslop", "keeps-command.md")
        self.assertRegex("Run kubectl rollout undo deployment/eta-api --namespace shipments now", cmd)
        self.assertNotRegex("kubectl rollout undo deployment/eta-api -n shipments", cmd)
        path = pattern("routing-unslop", "keeps-path.md")
        self.assertRegex("`src/shipments/eta.py`", path)
        self.assertNotRegex("src/shipments/eta_py", path)
        dash = pattern("routing-unslop", "no-dash.md")
        self.assertRegex("a pivotal moment \u2014 for the team", dash)
        self.assertNotRegex("a key moment, for the team", dash)
        history = pattern("routing-why-history", "read-history.md")
        self.assertRegex(json.dumps({"command": "git log --follow -p src/shipments/eta.py"}), history)
        self.assertRegex(json.dumps({"command": "git -C . blame src/shipments/eta.py"}), history)
        self.assertRegex(json.dumps({"command": "git --no-pager log -p src/shipments/eta.py"}), history)
        self.assertRegex(json.dumps({"command": "git -P log -p src/shipments/eta.py"}), history)
        self.assertNotRegex(json.dumps({"command": "cat src/shipments/eta.py"}), history)
        fired = pattern("routing-why-history", "fired.md")
        self.assertRegex(json.dumps({"skill": "aidlc:why"}), fired)
        self.assertNotRegex(json.dumps({"skill": "aidlc:how"}), fired)


class FinalReviewTest(unittest.TestCase):
    """Final review fixes: the never-list, the credit and the line width."""

    def test_the_design_carries_the_never_list(self):
        self.assertIn("- Never change code, commands, file paths, identifiers, quoted text, test output, a template's "
                      "fixed lines or a line another skill reads by its exact words (an index row, a FIELD line, a "
                      "status word, a commit trailer).", read("docs/design/2026-11-22-write-plainly.md"))

    def test_the_notice_credits_the_diataxis_step(self):
        self.assertIn("and the Diátaxis step in `writing-documentation` (from pstack's `technical-writing`) (Plan 29).",
                      flat(read("skills/NOTICE")))

    def test_the_new_lines_wrap(self):
        self.assertIn("flows through them,\n   where things live", skill_md("how"))
        inv = read("skills/story-run/references/playbook-investigation.md")
        self.assertIn("costs.\n   Write the finding through `unslop`", inv)
        for rel, marker in (("skills/how/SKILL.md", "3. Keep its citations"),
                            ("skills/story-run/references/playbook-investigation.md", "3. Write the finding")):
            lines = read(rel).splitlines()
            start = next(i for i, l in enumerate(lines) if l.startswith(marker))
            for n in range(start, start + 4):
                self.assertLessEqual(len(lines[n]), 125, f"{rel}:{n + 1}")


class DocsTest(unittest.TestCase):
    """Task 5: the change list after Plan 29; aidlc 8.2.0."""

    def test_the_change_list_and_the_version(self):
        changes = flat(read("docs/design/2026-11-19-aidlc-6-change-list.md").split("## 13. After Plan 29 (2026-11-22)", 1)[1])
        for phrase in ("`docs/plans/2026-11-22-plan-29-write-plainly.md`", "aidlc 8.2.0", "`unslop`",
                       "`technical-writing`", "`in-your-own-words`", "`how`", "`why`", "keeping pstack's names"):
            self.assertIn(phrase, changes, phrase)
        self.assertEqual(json.loads(read(".claude-plugin/plugin.json"))["version"], "8.2.0")


class RecordTest(unittest.TestCase):
    """Task 6: the verification record."""

    def test_the_record(self):
        record = read("docs/verification/2026-11-22-plan-29.md")
        for heading in ("## What changed", "## Checks", "## Rulings", "## For the owner"):
            self.assertIn(heading, record, heading)
        for phrase in ("aidlc 8.2.0", "`unslop`", "`technical-writing`", "`in-your-own-words`", "`how`", "`why`"):
            self.assertIn(phrase, record, phrase)


if __name__ == "__main__":
    unittest.main()
