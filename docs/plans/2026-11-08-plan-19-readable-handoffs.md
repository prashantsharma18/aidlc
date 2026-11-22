# Readable hand-offs Implementation Plan (Plan 19)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A person reviewing any hand-off document an `aidlc-*` stage drafts sees every unfilled gap, finds the decision asked of them on the first screen, and, where the document is read rendered, reads sections rather than a wall of text.

**Architecture:** Template edits under `skills/aidlc-*/assets/`, two sentences in two skills, one line in `AGENTS.md`, and small tolerance changes in the two starter scripts that read filled documents. One new test file, `scripts/test_handoffs.py`, pins the result; its tests are written first and seen failing.

**Tech Stack:** Markdown (GitHub's renderer), Python 3.12 standard library (`unittest`).

**Spec:** the owner's decision of 2026-11-08: do the three changes worth doing from the template readability review, and leave the rest. The review's findings are summarised below; they come from a read-only review that ran every template through GitHub's renderer (`gh api markdown`).

Branch: `docs/plan-19-readable-handoffs`. Builds on `main` at f235495 (aidlc 5.0.0, unreleased).

## The three changes

| # | Change | Why | Where |
|---|---|---|---|
| 1 | Placeholders stay visible | GitHub treats a placeholder that starts with a letter (`<engineer>`, `<product owner>`, `<YYYY-MM-DD>`) as an HTML tag and drops it, so a half-filled document renders with blanks: `CONFIRMED <engineer>, <YYYY-MM-DD>` shows as ", " | Every template with such a placeholder |
| 2 | Every document a person approves opens with "For the reviewer" | The decision asked of the reviewer sat on the last line | 14 approval documents |
| 3 | Documents read rendered become sections, lists and tables | Lines of `LABEL   value` with no blank lines merge into one paragraph | The PR description, evidence table, readiness, change record, incident record; the story index's header |

## Out of scope (the owner's decision)

One standard header and approval-line format across all templates; tables for decision options and security areas; explaining internal codes (L0–L3, "(B5)", tier dials); moving authoring notes out of filled documents; splitting the task bundle; fixing the front matter of `coordination-plan.md` and `compat-matrix.md` (it names the wrong stage); one variant of `tiers.md`; templates for the five documents that have none. Templates the review judged good keep their structure.

## Decisions this plan makes

| Question | Decision | Why |
|---|---|---|
| How placeholders stay visible | Two ways. A block of `FIELD   value` lines goes inside a ```` ```text ```` fence and keeps its `<…>` placeholders: a fence shows them as typed, keeps the alignment, and leaves every line byte-identical. Outside a fence, a placeholder is written `{{…}}`, the style the templates already use for `{{KEY}}` | Fencing keeps every test that pins a template line passing unchanged, and keeps the compact layout the agent and the scripts read |
| Which documents are fenced | The field-block documents read as source or by the agent: intent, evidence pack, design note, new system, plan, task bundle, fix brief, feature brief, coordination plan, explorer brief, decision frame, security review, release runbook, runbook; and the story index's header lines | They are reviewed in the pull request diff, or read by `aidlc-build`, `run_slices.py` and `story_status.py` |
| Which documents are rewritten | The five read rendered as whole documents: the PR description (it becomes the pull request body), the evidence table (linked from the pull request), readiness, the change record (pasted into change management), the incident record | A fence would make them a code box where people read prose |
| Which are converted only | ADR, agents-md, codebase map, compat matrix, progress note, spec, workspace, review record: `<word…>` outside code becomes `{{word…}}`; nothing else changes | They already use headings and tables |
| A placeholder that renders anyway (`<...>`, `<1|2|3>`) | Left as it is | Only a `<` followed by a letter is read as a tag |
| The decision block | A `## For the reviewer` section of four bullets under the title: who is asked and what they decide, where they record it, the tier and main risk, what changed since the last version. The first two are written into each template from its skill's Gate; the last two are placeholders | The reviewer learns their job before the details; the template cannot drift from the Gate because a test compares them |
| Scripts | `story_status.py` skips fence lines in the PARTS block and treats `{{` as a placeholder like `<`; `run_slices.py`'s `field()` treats `{{` as a placeholder like `<` | Filled documents keep parsing; old documents (with `<`) still parse |
| Version | None: aidlc 5.0.0 is not yet released | A test pins 5.0.0; these changes join it |

## Global Constraints

- Never change an existing test assertion: every `scripts/test_*.py` test keeps passing unchanged; new checks are new tests. Lines that existing tests pin stay byte-identical (fencing a block does not change its lines).
- The two copies of `story-index.md` (in `aidlc-start` and `aidlc-plan`) and of `incident.md` (in `aidlc-operate` and `aidlc-feedback`) stay identical.
- No gate changes: who approves, and where, comes from each skill's Gate, unchanged.
- Short sentences, British spelling. No new dependency. Commits use the noreply identity and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push.

## Review Focus

- A filled coordination plan whose PARTS block now sits inside a fence. A person expects `story_status.py` to read its parts as before; Task 1 adds `test_parts_inside_a_fence_are_read`.
- A filled bundle or brief with a fence around its fields. A person expects `run_slices.py` to read MODE, TIER and CONFIRMED as before; Task 1 adds `test_fields_inside_a_fence_are_read`.
- A template still using `<word>` outside code after the change. A person expects the gap to show; Task 6 adds `test_no_template_has_a_placeholder_that_vanishes`.
- A "For the reviewer" block naming someone other than the skill's Gate. A person expects one answer; Task 5 adds `test_each_decision_block_matches_its_gate`.
- A rewritten document that drops a label a skill names (the incident record's Prevention and Measures; the evidence table's Unproved). Task 4 adds `test_rewritten_documents_keep_the_labels_skills_name`.

---

### Task 1: The scripts read the new format

**Files:**
- Modify: `starter/workspace/scripts/story_status.py`, `starter/repo/scripts/run_slices.py`
- Test: `scripts/test_story_status.py`, `scripts/test_run_slices.py` (new tests only)

- [ ] **Step 1: Write the failing tests.** Append to `scripts/test_story_status.py`, inside its main test class (find it with `grep -n "^class" scripts/test_story_status.py`; use the module's own import name for the script, as its other tests do):

```python
    def test_parts_inside_a_fence_are_read(self):
        plan = ("# Coordination plan · SHIP-1 · x · v1\n\n```text\n"
                "OUTCOME    something. Tier 2\n"
                "PARTS      #  Repository     Owner    Change\n"
                "           1  shipments-api  core     add the field\n"
                "           2  web-portal     web      show the field\n"
                "```\n")  # the closing fence falls inside the PARTS block
        parts, unread = story_status.read_parts(plan)
        self.assertEqual(parts, [(1, "shipments-api"), (2, "web-portal")])
        self.assertEqual(unread, [])

    def test_curly_placeholders_are_not_versions(self):
        self.assertEqual(story_status.items("spec v{{n}} · contract none"), [])
```

Append to `scripts/test_run_slices.py`, inside `class FieldTest`:

```python
    def test_curly_placeholders_are_no_value(self):
        self.assertIsNone(run_slices.field("MODE        {{hands-on | delegate}}\n", "MODE"))

    def test_fields_inside_a_fence_are_read(self):
        text = "# x\n\n```text\nTIER        1 (why)\nMODE        delegate   (note)\n```\n"
        self.assertEqual((run_slices.field(text, "MODE"), run_slices.tier(text)), ("delegate", 1))
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest scripts.test_story_status scripts.test_run_slices 2>&1 | grep -E "^FAIL:|^ERROR:|^FAILED|^OK"`
Expected: `test_parts_inside_a_fence_are_read` fails (the closing fence is reported unread), `test_curly_placeholders_are_not_versions` fails, `test_curly_placeholders_are_no_value` fails. `test_fields_inside_a_fence_are_read` passes already (it guards against a regression); note it.

If `items()` returns something other than a list for that input, read `items()` first and adapt only the test's expected value to its return type, never the function's behaviour on `<`.

- [ ] **Step 3: Make them pass.**
  - `story_status.py`, `read_parts`: before the existing skip condition, add `if line.strip().startswith("```"): continue`. In the skip condition `"<" in line`, also skip `"{{" in line`.
  - `story_status.py`, `items`: where an item containing `"<"` is skipped, also skip one containing `"{{"`.
  - `run_slices.py`, `field`: return `None` when the value starts with `<` or with `{{`.

- [ ] **Step 4: Run all tests.** Expected: `OK`.

- [ ] **Step 5: Commit** ("fix(starter): the scripts read fenced fields and {{…}} placeholders").

---

### Task 2: Fence the field blocks

**Files:**
- Modify: `skills/aidlc-intent/assets/intent.md`, `skills/aidlc-discover/assets/evidence-pack.md`, `skills/aidlc-design/assets/design-note.md`, `skills/aidlc-design/assets/new-system.md`, `skills/aidlc-design/assets/coordination-plan.md`, `skills/aidlc-design/assets/decision-frame.md`, `skills/aidlc-plan/assets/plan.md`, `skills/aidlc-plan/assets/task-bundle.md`, `skills/aidlc-plan/assets/fix-brief.md`, `skills/aidlc-plan/assets/feature-brief.md`, `skills/aidlc-discover/assets/explorer-brief.md`, `skills/aidlc-onboard/assets/explorer-brief.md`, `skills/aidlc-review/assets/security-review.md`, `skills/aidlc-release/assets/release-runbook.md`, `skills/aidlc-operate/assets/runbook.md`, `skills/aidlc-start/assets/story-index.md`, `skills/aidlc-plan/assets/story-index.md`
- Create: `scripts/test_handoffs.py`

**Interfaces:**
- Produces: `scripts/test_handoffs.py` with `read(rel)`, `outside_code(text)`, `VANISHING`, `vanishing(rel)` and `class HandoffsTest`; later tasks append inside it.

- [ ] **Step 1: Write the failing tests.** Create `scripts/test_handoffs.py`:

```python
"""Plan 19: hand-off documents a person reviews show every gap, open with the decision, and read as sections."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VANISHING = re.compile(r"<[A-Za-z][^<>\n]*>")  # GitHub reads <word ...> as an HTML tag and drops it
FENCED = ["aidlc-intent/assets/intent.md", "aidlc-discover/assets/evidence-pack.md",
          "aidlc-design/assets/design-note.md", "aidlc-design/assets/new-system.md",
          "aidlc-design/assets/coordination-plan.md", "aidlc-design/assets/decision-frame.md",
          "aidlc-plan/assets/plan.md", "aidlc-plan/assets/task-bundle.md", "aidlc-plan/assets/fix-brief.md",
          "aidlc-plan/assets/feature-brief.md", "aidlc-discover/assets/explorer-brief.md",
          "aidlc-onboard/assets/explorer-brief.md", "aidlc-review/assets/security-review.md",
          "aidlc-release/assets/release-runbook.md", "aidlc-operate/assets/runbook.md",
          "aidlc-start/assets/story-index.md", "aidlc-plan/assets/story-index.md"]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def vanishing(rel: str) -> list[str]:
    return VANISHING.findall(outside_code(read(rel)))


class HandoffsTest(unittest.TestCase):
    def test_field_blocks_sit_in_text_fences(self):
        for name in FENCED:
            rel = f"skills/{name}"
            text = read(rel)
            self.assertIn("```text\n", text, rel)
            self.assertEqual(text.count("```") % 2, 0, rel)
            self.assertEqual(vanishing(rel), [], rel)
            self.assertNotRegex(outside_code(text), r"(?m)^[A-Z][A-Z /-]{2,}\s{2,}\S", rel)

    def test_every_fence_is_a_text_fence(self):
        for path in sorted((ROOT / "skills").glob("aidlc-*/assets/*.md")):
            for opening in re.findall(r"(?m)^```(\S*)$", path.read_text(encoding="utf-8"))[::2]:
                self.assertEqual(opening, "text", path)

    def test_copies_stay_identical(self):
        self.assertEqual(read("skills/aidlc-start/assets/story-index.md"),
                         read("skills/aidlc-plan/assets/story-index.md"))
        self.assertEqual(read("skills/aidlc-discover/assets/explorer-brief.md"),
                         read("skills/aidlc-onboard/assets/explorer-brief.md"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them and watch them fail.** Run: `python3 -m unittest scripts.test_handoffs 2>&1 | tail -1`. Expected: `test_field_blocks_sit_in_text_fences` fails; the other two pass (guards).

- [ ] **Step 3: Fence each file.** In every edit, the lines inside the fence stay byte-identical: only the fence lines and, where named, a heading are added. A fence opens with a line ```` ```text ```` and closes with a line ```` ``` ````, each on its own line, with a blank line before the opening and after the closing.
  - `intent.md`: fence from the `Kind` line through the `(dials: …)` line. The heading and the `Gate:` line stay outside.
  - `evidence-pack.md`: fence from `QUESTION` through `DECISION`.
  - `design-note.md`: fence from the line beginning `1 Does it change` through `APPROVED`.
  - `new-system.md`: add `# {{KEY}} · {{TITLE}} · new system` and a blank line after the marker comment; fence from the `NEW SYSTEM ·` line through `APPROVED`.
  - `coordination-plan.md`: after the front matter, replace the title line `Coordination plan · {{KEY}} · {{TITLE}} · v1` with `# Coordination plan · {{KEY}} · {{TITLE}} · v1` and a blank line; fence from `OUTCOME` to the end.
  - `decision-frame.md`: two fences: from `Decision` through `Unknown`, and from `FACT` through `AGAINST`. The headings stay outside.
  - `plan.md`: replace the heading `# Plan: {{KEY}} · {{TITLE}}            Spec: <version, clarifications>` with `# Plan: {{KEY}} · {{TITLE}}`; fence from a new first line `SPEC       <version, clarifications>` (inserted above `APPROACH`) through `APPROVAL`.
  - `task-bundle.md`: add `# {{KEY}} · task bundle · {{SLICE}}` and a blank line after the marker; fence from the `TASK BUNDLE ·` line through `INCLUDED`.
  - `fix-brief.md`, `feature-brief.md`: add `# {{KEY}} · fix brief` (or `# {{KEY}} · feature brief`) and a blank line after the marker; fence from the `FIX BRIEF ·` (or `FEATURE BRIEF ·`) line through `CONFIRMED`.
  - Both `explorer-brief.md` copies: fence from `Explorer brief` to the end; the copies stay identical.
  - `security-review.md`: add `# Security review · {{KEY}} · {{PR}}` and a blank line after the marker; fence from the `Security review record ·` line to the end.
  - `release-runbook.md`: add `# Release runbook · {{KEY}}` and a blank line after the marker; fence from the `Release runbook ·` line to the end.
  - `runbook.md`: fence from `ALERT` to the end.
  - Both `story-index.md` copies: fence from `SOURCE` through `UNAFFECTED`. The paragraph and the stage table stay outside. In the paragraph, replace "done, or stopped: <reason>." with "done, or `stopped: <reason>`."; in the table's template row, replace `| <stage> | <repository or workspace root> | to do |` with `| {{stage}} | {{repository or workspace root}} | to do |`. The copies stay identical.

- [ ] **Step 4: Run all tests and the validator.** Expected: `OK` (every pinned template line is unchanged); 0 problems. If an existing test fails, a line inside a fence changed: restore it byte for byte.

- [ ] **Step 5: Commit** ("docs(templates): field blocks in text fences, so placeholders show and alignment holds").

---

### Task 3: Convert the stray placeholders

**Files:**
- Modify: `skills/aidlc-design/assets/adr.md`, `skills/aidlc-onboard/assets/agents-md.md`, `skills/aidlc-onboard/assets/codebase-map.md`, `skills/aidlc-release/assets/compat-matrix.md`, `skills/aidlc-build/assets/progress-note.md`, `skills/aidlc-specify/assets/spec.md`, `skills/aidlc-onboard/assets/workspace.md`, `skills/aidlc-review/assets/review-record.md`
- Test: `scripts/test_handoffs.py`

- [ ] **Step 1: Write the failing test.** Append inside `class HandoffsTest`:

```python
    CONVERTED = ["aidlc-design/assets/adr.md", "aidlc-onboard/assets/agents-md.md",
                 "aidlc-onboard/assets/codebase-map.md", "aidlc-release/assets/compat-matrix.md",
                 "aidlc-build/assets/progress-note.md", "aidlc-specify/assets/spec.md",
                 "aidlc-onboard/assets/workspace.md", "aidlc-review/assets/review-record.md"]

    def test_heading_documents_write_placeholders_in_braces(self):
        for name in self.CONVERTED:
            rel = f"skills/{name}"
            self.assertEqual(vanishing(rel), [], rel)
            self.assertIn("{{", read(rel), rel)
```

- [ ] **Step 2: Run it and watch it fail.** Expected: 1 FAIL listing the first file with `<word>` outside code.

- [ ] **Step 3: Convert.** For each file, replace every `<…>` that starts with a letter and lies outside a fenced block, an HTML comment or a code span, with `{{…}}` holding the same words. Do it with this one-off script, then read every hunk of `git diff`:

```python
import re
from pathlib import Path
CODE = re.compile(r"(?ms)^```[a-z]*\n.*?^```$|<!--.*?-->|`[^`\n]*`")
TAG = re.compile(r"<([A-Za-z][^<>\n]*)>")
for name in ("aidlc-design/assets/adr.md", "aidlc-onboard/assets/agents-md.md", "aidlc-onboard/assets/codebase-map.md",
             "aidlc-release/assets/compat-matrix.md", "aidlc-build/assets/progress-note.md",
             "aidlc-specify/assets/spec.md", "aidlc-onboard/assets/workspace.md",
             "aidlc-review/assets/review-record.md"):
    path = Path("skills") / name
    text, out, last = path.read_text(encoding="utf-8"), [], 0
    for m in CODE.finditer(text):
        out.append(TAG.sub(r"{{\1}}", text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(TAG.sub(r"{{\1}}", text[last:]))
    path.write_text("".join(out), encoding="utf-8")
```

- [ ] **Step 4: Run all tests and the validator.** Expected: `OK`; 0 problems. If an existing test pins a converted string, restore that string and put it in a code span instead; record the ruling.

- [ ] **Step 5: Commit** ("docs(templates): placeholders outside code are written {{…}}, so they show when rendered").

---

### Task 4: Rewrite the five documents people read rendered

**Files:**
- Modify: `skills/aidlc-review/assets/pr-description.md`, `skills/aidlc-verify/assets/evidence-table.md`, `skills/aidlc-release/assets/readiness.md`, `skills/aidlc-release/assets/change-record.md`, `skills/aidlc-operate/assets/incident.md`, `skills/aidlc-feedback/assets/incident.md`, `skills/aidlc-verify/SKILL.md`, `skills/aidlc-release/SKILL.md`
- Test: `scripts/test_handoffs.py`

- [ ] **Step 1: Write the failing tests.** Append inside `class HandoffsTest`:

```python
    REWRITTEN = ["aidlc-review/assets/pr-description.md", "aidlc-verify/assets/evidence-table.md",
                 "aidlc-release/assets/readiness.md", "aidlc-release/assets/change-record.md",
                 "aidlc-operate/assets/incident.md"]

    def test_rendered_documents_read_as_sections(self):
        for name in self.REWRITTEN:
            rel = f"skills/{name}"
            text = read(rel)
            self.assertRegex(text, r"(?m)^# ", rel)
            self.assertGreaterEqual(len(re.findall(r"(?m)^## ", text)), 3, rel)
            self.assertNotRegex(outside_code(text), r"(?m)^[A-Z][A-Z /-]{2,}\s{2,}\S", rel)
            self.assertEqual(vanishing(rel), [], rel)
        self.assertEqual(read("skills/aidlc-operate/assets/incident.md"),
                         read("skills/aidlc-feedback/assets/incident.md"))

    def test_rewritten_documents_keep_the_labels_skills_name(self):
        incident = read("skills/aidlc-operate/assets/incident.md")
        self.assertIn("## Prevention", incident)
        self.assertIn("## Measures", incident)
        evidence = read("skills/aidlc-verify/assets/evidence-table.md")
        self.assertIn("## Unproved", evidence)
        self.assertIn("plans/<KEY>/** exempt", evidence)
        self.assertIn("| Criterion | Test | Local | Trusted CI |", evidence)
        readiness = read("skills/aidlc-release/assets/readiness.md")
        self.assertEqual(readiness.count("- [ ] "), 10)
        verify = " ".join(read("skills/aidlc-verify/SKILL.md").split())
        self.assertNotIn("UNPROVED", verify)
        release = " ".join(read("skills/aidlc-release/SKILL.md").split())
        self.assertNotIn("in a column of `assets/readiness.md`", release)
        self.assertIn("under its heading in `assets/readiness.md`", release)
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 2 FAIL.

- [ ] **Step 3: Write the five templates** with exactly this content (both `incident.md` copies get the same text). Task 5 adds the "For the reviewer" sections; do not add them here.

`skills/aidlc-review/assets/pr-description.md`:

````markdown
<!-- aidlc template: pr-description -->
# [{{KEY}}] {{SLICE}}

## Summary
{{one or two sentences: what this pull request does, and why}}

## What changed
- {{change}}: {{the criterion it serves}}

## Not changed
- {{what deliberately did not change}}

## Questions for the reviewers
- {{one concrete question per reviewer or specialist}}

## Decisions made while building
- {{decision}}: confirm with {{who}}

## Traceability
- **Work item:** {{key, title}} · Tier {{n}}
- **Spec:** {{version, clarifications}}
- **Plan:** plan.md {{version}} ({{commit}}), approved by {{who}} on {{YYYY-MM-DD}}
- **Bundle or brief:** {{path}} at its approval commit
- **Recipe:** {{sha, tool@version, recipe check output}}, or none
- **Evidence:** {{link to the evidence table from the trusted run; what was proved only in CI}}
- **Assumptions:** {{assumption, or none}}

## Rollback
{{how; or "nothing at merge: the flag stays off"}}
````

`skills/aidlc-verify/assets/evidence-table.md`:

````markdown
<!-- aidlc template: evidence-table -->
# {{KEY}} · {{PART}} · evidence

From the trusted run, never the agent's summary.

**Verdict:** {{every criterion proved in the trusted run, or the number unproved, listed under Unproved}}

## Criteria
| Criterion | Test | Local | Trusted CI |
|---|---|---|---|
| AC1 | {{test name containing AC1}} | {{pass, fail or SKIPPED}} | {{pass or fail}} |

Total in CI: {{n}} tests ({{passed}} passed, {{failed}} failed, {{skipped}} skipped).

## Integrity and scans

```text
                                                            LOCAL  TRUSTED CI
INTEGRITY  scope: every changed path inside MAY CHANGE (plans/<KEY>/** exempt)      <ok>   <ok (trusted copy)>
           protected tests: no existing line changed       -      <ok>
           skips: tests that did not run                   <n>    <0>
SCANS      dependency, secrets, SAST                        -      <clean>
```

## AI review
- {{finding}}: {{fixed test-first, or dismissed: reason}}

## Unproved
- {{criterion, why, who accepted}}, or none
````

`skills/aidlc-release/assets/readiness.md`:

````markdown
<!-- aidlc template: readiness -->
# {{KEY}} · readiness

The worst of the five decides.

## 1. Scope known
- [ ] Users: {{what people experience, including refusals}}
- [ ] Services and blast radius: {{services}}
- [ ] Success signal: {{signal}}

## 2. Evidence passing
- [ ] Required checks green and code-owner approval on every PR; specialist reviews recorded
- [ ] Staging behaviour confirmed: {{what was seen}}

## 3. Access limited
- [ ] Who may change the flag or configuration in production: {{who}}; no agent or pipeline identity can

## 4. Monitoring in place
- [ ] Monitoring checked against the `adding-observability` pre-launch list: alerts with thresholds, routed to {{on-call}}, each pointing to a runbook
- [ ] Dashboard: {{link}}

## 5. Recovery defined
- [ ] Rollback: {{fastest route}}, pre-approved for on-call, rehearsed in staging on {{YYYY-MM-DD}}
- [ ] Runbook: {{path}}

## Decision
{{ship, limit or hold}}. Release approver: {{name}}, {{YYYY-MM-DD}}
````

`skills/aidlc-release/assets/change-record.md`:

````markdown
<!-- aidlc template: change-record -->
# {{KEY}} · change record

## Change
- **What:** {{what is switched or deployed}}
- **Artefact:** build of commit {{sha}}; digest recorded by the release pipeline
- **Tier:** {{n}}
- **Links:** {{work item; spec version; plan; pull requests with evidence and reviews; readiness}}

## Plan
1. {{staging step}}
2. {{rehearse rollback}}
3. {{production step}}
4. {{watch window}}

## Stop and caution
- **Stop:** {{signal, threshold, duration}} -> {{action at once, by whom, with no further approval}}
- **Caution:** {{signal}} -> hold the next stage; follow the runbook

## Roles
- **Agent:** read-only: summaries and proposals; no flags, configuration or credentials
- **Submitted by:** {{engineer}}, drafted with the agent
- **Approved by:** {{release approver}}, in change management

## Follow-ups
- Flag removal: {{owner, date, work item}}
````

`incident.md` (both copies):

````markdown
<!-- aidlc template: incident -->
# {{KEY}} · incident record

- **Title:** {{title}}
- **Severity:** {{severity}}
- **Impact:** {{who, what, from and to}}
- **Contained:** {{action}}. Undo: {{step and its trigger}}
- **Cause:** {{confirmed cause}} (confirmed by {{person}}, {{time}})

## Timeline
- {{hh:mm}} {{event}}

## Actions
| ID | Action | Owner | Due |
|---|---|---|---|
| A1 | {{action}} | {{owner}} | {{YYYY-MM-DD}} |

## Prevention
- {{lesson}} -> {{test, eval case, context, guardrail, review checklist or measure}} -> {{where it went}}

## Measures
- {{counted as a failed change? rework?}}

The record closes only when every prevention change is merged or explicitly declined.
````

- [ ] **Step 4: Update the two skill sentences.**
  - `aidlc-verify/SKILL.md`: replace "5. Under UNPROVED, list" with "5. Under Unproved, list"; replace "List it under UNPROVED." with "List it under Unproved."; replace "- UNPROVED says \"none\" while a test was skipped." with "- Unproved says \"none\" while a test was skipped.".
  - `aidlc-release/SKILL.md`: replace "Place each in a column of `assets/readiness.md`; the worst column decides. For the monitoring column, load" with "Record each under its heading in `assets/readiness.md`; the worst one decides. For monitoring, load".

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit** ("docs(templates): the PR description, evidence table, readiness, change record and incident record read as sections").

---

### Task 5: "For the reviewer" on every approval document

**Files:**
- Modify: the 14 templates in the table below
- Test: `scripts/test_handoffs.py`

Each block goes directly under the document's `#` title (after the spec's owner line, for `spec.md`), as:

```markdown
## For the reviewer
- **Asked of:** <who, to decide what: from the table>
- **Record it:** <where: from the table>
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}
```

| Template | Asked of | Record it |
|---|---|---|
| `aidlc-intent/assets/intent.md` | The product owner, to accept or decline the work, set its priority and agree the provisional tier with whoever owns the risk | In the tracker |
| `aidlc-specify/assets/spec.md` | The spec owner, to approve the criteria and decide every edge case; a specialist reviews at Tier 3 | On the work item: "Spec vN approved by name" |
| `aidlc-discover/assets/evidence-pack.md` | The tech lead, with the affected owners, to proceed, escalate or raise the tier | On the DECISION line below, and on the work item |
| `aidlc-design/assets/design-note.md` | The tech lead or architect, to approve the design or record "none needed"; consumers approve a contract change | On the APPROVED or RECORDED BY line below, and on the work item with this note's version and commit |
| `aidlc-design/assets/new-system.md` | The tech lead or architect, to approve the stack, every dependency and the scaffold commands | On the APPROVED line below, and on the work item with this file's version and commit |
| `aidlc-plan/assets/plan.md` | The tech lead, to approve the plan and its bundles | On the work item, with the plan's version and commit |
| `aidlc-plan/assets/task-bundle.md` | The tech lead, to approve this slice, its MODE and its boundaries | On the work item with the plan's version and commit; a changed bundle is approved again |
| `aidlc-plan/assets/fix-brief.md` | The engineer, to confirm the brief and choose its MODE; the code owner approves it with the fix | On the CONFIRMED line below; then in the pull request |
| `aidlc-plan/assets/feature-brief.md` | The engineer, to confirm the brief and choose its MODE; the code owner approves it with the change | On the CONFIRMED line below; then in the pull request |
| `aidlc-review/assets/pr-description.md` | A code owner who neither wrote nor pushed the change, to approve the merge; a required specialist can block | In the pull request |
| `aidlc-review/assets/review-record.md` | The engineer, to decide each finding (high and medium block the merge); then a code owner, to approve | In the findings and the DECISION below; the approval in the pull request |
| `aidlc-review/assets/security-review.md` | The security champion (the required specialist), to clear or block the change; a code owner approves | On the GATE line below, and in the pull request |
| `aidlc-release/assets/readiness.md` | The release approver, to decide ship, limit or hold; the owning team confirms monitoring and rollback | In change management |
| `aidlc-release/assets/change-record.md` | The release approver, to approve the change and its stop criteria | In change management |

- [ ] **Step 1: Write the failing test.** Append inside `class HandoffsTest`:

```python
    APPROVALS = {
        "aidlc-intent/assets/intent.md": ("aidlc-intent", "product owner", "tracker"),
        "aidlc-specify/assets/spec.md": ("aidlc-specify", "spec owner", "work item"),
        "aidlc-discover/assets/evidence-pack.md": ("aidlc-discover", "tech lead", "DECISION line"),
        "aidlc-design/assets/design-note.md": ("aidlc-design", "tech lead or architect", "APPROVED"),
        "aidlc-design/assets/new-system.md": ("aidlc-design", "tech lead or architect", "APPROVED line"),
        "aidlc-plan/assets/plan.md": ("aidlc-plan", "tech lead", "work item"),
        "aidlc-plan/assets/task-bundle.md": ("aidlc-plan", "tech lead", "work item"),
        "aidlc-plan/assets/fix-brief.md": ("aidlc-plan", "engineer", "CONFIRMED line"),
        "aidlc-plan/assets/feature-brief.md": ("aidlc-plan", "engineer", "CONFIRMED line"),
        "aidlc-review/assets/pr-description.md": ("aidlc-review", "code owner", "pull request"),
        "aidlc-review/assets/review-record.md": ("aidlc-review", "code owner", "DECISION"),
        "aidlc-review/assets/security-review.md": ("aidlc-review", "specialist", "GATE line"),
        "aidlc-release/assets/readiness.md": ("aidlc-release", "release approver", "change management"),
        "aidlc-release/assets/change-record.md": ("aidlc-release", "release approver", "change management"),
    }

    def test_each_approval_document_opens_with_the_decision(self):
        for name in self.APPROVALS:
            text = read(f"skills/{name}")
            block = text.index("## For the reviewer")
            first_fence = text.find("```")
            other_sections = [m.start() for m in re.finditer(r"(?m)^## (?!For the reviewer)", text)]
            self.assertTrue(first_fence < 0 or block < first_fence, name)
            self.assertTrue(not other_sections or block < min(other_sections), name)
            for label in ("**Asked of:**", "**Record it:**", "**Tier and main risk:**",
                          "**Changed since the last version:**"):
                self.assertIn(label, text, name)
            self.assertEqual(vanishing(f"skills/{name}"), [], name)

    def test_each_decision_block_matches_its_gate(self):
        for name, (skill, who, where) in self.APPROVALS.items():
            block = read(f"skills/{name}").split("## For the reviewer", 1)[1].split("\n## ", 1)[0]
            block = " ".join(block.split())
            gate = " ".join(read(f"skills/{skill}/SKILL.md").split("## Gate", 1)[1].split("\n## ", 1)[0].split())
            self.assertIn(who, block.lower(), name)
            self.assertIn(where, block, name)
            self.assertIn(who.split(" or ")[0], gate.lower(), f"{name}: the Gate of {skill} does not name {who}")
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 2 ERROR or FAIL (no block yet).

- [ ] **Step 3: Add the 14 blocks** from the table. In a fenced template the block goes above the fence; in `spec.md` it goes after the `Spec owner: …` line and before `## Outcome`; in `pr-description.md` before `## Summary`; in `readiness.md` after "The worst of the five decides."; in `change-record.md` before `## Change`; in `review-record.md` after the title, before the `Reviewer:` line.

- [ ] **Step 4: Run all tests and the validator.** Expected: `OK`; 0 problems. If the Gate check fails for a template, the table above disagrees with the skill: fix the block to the skill's words, never the skill.

- [ ] **Step 5: Commit** ("docs(templates): every approval document opens with For the reviewer").

---

### Task 6: The rule, the guard, the record

**Files:**
- Modify: `AGENTS.md`, `scripts/test_handoffs.py`
- Create: `docs/verification/2026-11-08-plan-19-readable-handoffs.md`

- [ ] **Step 1: Write the failing tests.** Append inside `class HandoffsTest`:

```python
    def test_no_template_has_a_placeholder_that_vanishes(self):
        offenders = {}
        for path in sorted((ROOT / "skills").glob("aidlc-*/assets/*.md")):
            rel = str(path.relative_to(ROOT))
            found = vanishing(rel)
            if found:
                offenders[rel] = found[:3]
        self.assertEqual(offenders, {})

    def test_agents_md_states_the_template_rule(self):
        text = " ".join(read("AGENTS.md").split())
        self.assertIn("a placeholder outside a code block is written `{{…}}`", text)
        self.assertIn("a block of FIELD lines sits in a ```text fence", text)
        self.assertIn("opens with a `## For the reviewer` section", text)
```

- [ ] **Step 2: Run them.** Expected: `test_no_template_has_a_placeholder_that_vanishes` passes if Tasks 2 to 4 covered every template (record which); if it fails, the listed file was missed: fence or convert it as in Task 2 or 3. `test_agents_md_states_the_template_rule` fails.

- [ ] **Step 3: Add the rule to `AGENTS.md`'s Standards**, after the line about skills following the open format: "- Templates (`skills/aidlc-*/assets/`) are read rendered by the people who approve them: a placeholder outside a code block is written `{{…}}`, because GitHub drops `<word>` as an HTML tag; a block of FIELD lines sits in a ```text fence; and every document a person approves opens with a `## For the reviewer` section naming who decides, where they record it, the tier and main risk, and what changed."

- [ ] **Step 4: Run every check.**

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3
python3 scripts/validate.py | tail -1
python3 scripts/route_check.py | tail -1
claude plugin validate .
```

Expected: `OK` (308 plus Plan 19's tests); 0 problems; rank-1 unchanged (86%); `Validation passed` with the known warning.

- [ ] **Step 5: Render check (no cost).** For three templates (one fenced: `fix-brief.md`; one rewritten: `pr-description.md`; one converted: `spec.md`), render with GitHub's renderer and confirm every placeholder shows: `gh api markdown -f text="$(cat <file>)" -f mode=gfm | grep -c "{{\|&lt;"`. This sends the template text to GitHub's API; the templates hold no secret, and the repository is to be published there. If `gh` is not authenticated here, skip it and record that.

- [ ] **Step 6: Commit** ("docs: AGENTS.md states the template rule; a guard over every template").

- [ ] **Step 7: Final review.** A fresh reviewer on the most capable model reads the branch against this plan, checks every template the branch touched as rendered Markdown and as a diff, checks every "For the reviewer" block against its skill's Gate, and checks that the scripts still read filled documents. Fix critical, important and cheap real low findings test-first; dismiss other lows with a reason.

- [ ] **Step 8: Write the verification record** in Plan 18's layout: the checks, each Review Focus case with its test, the render check's result, the review's findings and fixes, and the decisions. Commit it with the fix pass.
