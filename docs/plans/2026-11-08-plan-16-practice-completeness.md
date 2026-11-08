# Practice completeness Implementation Plan (Plan 16, aidlc 4.4.0)

**Status: Parked (2026-11-08) by the owner, Prashant Sharma.** Not executed: the eight earlier practices stay as they are
for now. The research below (gaps, outdated statements, sources and proposed wording) is kept for when the plan is
picked up again. Nothing in the kit depends on it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The eight earlier practices state every principle an experienced engineer expects, in words that hold in any stack, with their code marked as illustrations; `securing-code` gains the five missing attack classes.

**Architecture:** Markdown edits to eight practice skills under `plugins/aidlc/skills/` and their `references/`, one description, one routing case, two language eval cases. One new test file, `scripts/test_practices.py`, pins each change; its tests are written first and seen failing. Edits are "replace A with B" pairs or "add after the line"; the file's line breaks may differ, so match the words and keep the file's wrapping.

**Tech Stack:** Markdown, Python 3.12 standard library (`unittest`), Claude Code for `claude plugin validate .` and `claude plugin eval`.

**Spec:** `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md` (section "Plan 16: practice completeness", and the "Languages" row of its decisions table). Builds on Plan 15 (aidlc 4.3.0, `main` at cffa074).

Branch: `docs/plan-16-practice-completeness`.

## Research

A completeness check ran on 2026-11-08 against current sources, one pass per practice. A gap counted only when an experienced engineer would expect the practice to cover it, it holds across stacks, the skill misses it, and a current authoritative source backs it; at most four per practice. The sources, for the reviewer and the verification record (they are not written into the skills):

| Practice | Sources |
|---|---|
| `securing-code` | OWASP Top 10 (A03 Injection, A08 Software and Data Integrity), OWASP API Security Top 10 2023 (API3), OWASP cheat sheets: Deserialization, XML External Entity Prevention, Mass Assignment, Server-Side Template Injection; OWASP ReDoS |
| `designing-apis` | Google AIP-180 (compatibility), AIP-158 (pagination); RFC 9110 §13.1.1 (If-Match); RFC 9457 (Problem Details, obsoletes RFC 7807) |
| `reviewing-code` | Google engineering practices, "What to look for in a code review"; Amazon Builders' Library on rollback safety and on timeouts, retries and backoff with jitter |
| `debugging-failures` | Google SRE book, "Effective Troubleshooting"; Go race detector documentation |
| `migrating-safely` | PostgreSQL `ALTER TABLE` and `lock_timeout` documentation; Stripe, "Online migrations at scale"; EF Core "Managing migrations"; Amazon Builders' Library on rollback safety |
| `building-user-interfaces` | W3C WCAG 2.2 (Recommendation since October 2023; 1.4.3, 1.4.4, 2.3.3, 2.4.11, 2.5.7, 2.5.8, 3.3.7, 3.3.8); W3C Internationalization quick tips; Android localisation guide |
| `adding-observability` | Google SRE workbook, "Alerting on SLOs"; OpenTelemetry logs specification and semantic conventions (HTTP metrics stable); W3C Trace Context; OpenTelemetry SDK shutdown |
| `tuning-performance` | Go diagnostics; flame graphs; Google SRE book, "Testing for Reliability"; JMH, BenchmarkDotNet, Go `testing.B`; Android vitals and MetricKit; Lighthouse 10 release notes (TTI removed from scoring); web.dev "Optimize long tasks" (`isInputPending` no longer recommended) |

## Decisions this plan makes where the spec is silent

| Question | Decision | Why |
|---|---|---|
| Code that sits in `SKILL.md` (four practices have no `references/`) | Stays where it is, with one line saying it is an illustration; not moved | The spec says "edited in place"; moving code into new files is a restructure |
| Which gaps | Every gap the check found: 5 security, 4 API, 3 review, 3 debugging, 4 migration, 3 UI, 4 observability, 4 performance. The fifth migration candidate (machine-readable deprecation markers) is left out | Each passed the four tests; the cap kept the list to what matters most |
| Outdated statements | Fixed: WCAG 2.1 to 2.2, large text, target size, Time to Interactive, `isInputPending`, HTTP status grouped by class, "write the `down`" for tools without one | A practice that teaches a superseded standard is a defect, not a gap |
| One-stack wording in `SKILL.md` | Rewritten as a general rule with a hint naming at least three stacks | The design's Languages decision |
| Sources | Named as standards in the text (WCAG 2.2, RFC 9457, OpenTelemetry semantic conventions, W3C Trace Context); no URLs added | The repository writes no third-party URLs beyond those already there |
| Evals | Re-run the three Plan 14 language cases; add `language-java-xxe` and `language-python-template-injection`; all within the owner's cap | The spec: "Plan 14's Java and .NET fixtures confirm the result; a miss is fixed in the principle" |

## Global Constraints

- General principles, with short hints that name several stacks. Never per-language reference files.
- Code examples stay in the patterns files (and, for the four practices without references, in `SKILL.md`), labelled as illustrations.
- The eight practices are edited in place; `plugins/aidlc/skills/NOTICE` stays. They keep their own section structure (`AGENTS.md`: "the eight earlier practices keep their own structure").
- New text is in original words, British spelling, short sentences. No third-party project, author or URL is added beyond the tools and standards named as hints.
- Never change an existing test assertion: every `scripts/test_*.py` test keeps passing unchanged; new checks are new tests. `scripts/test_loads.py`'s `LOADS` table stays exactly as it is. Phrases existing tests pin stay word for word; run the whole suite after every edit.
- A description stays under 1,024 characters and says "Use when". The routing check keeps rank-1 at or above 0.85.
- Paid eval runs only within a cap the owner approves. Do not work around the Bash sandbox check.
- Version: aidlc 4.4.0 (Task 7). Commits use the noreply identity and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A hint that is wrong for a stack it names (a default stated backwards, an API that does not exist). A person in that stack expects the hint to be true; the final reviewer checks each named API and default, and Task 7's record lists any it could not confirm.
- A rewrite that drops a rule while making it neutral (for example the cookie rule losing its CSRF reason). A person expects the same rule, wider; Tasks 1 to 6 keep a test on each rule's substance, not only its new wording.
- A new principle that contradicts a sibling practice (for example the review practice's timeout rule against `tuning-performance`, or mass assignment against `designing-apis`' input types). A person expects one answer across the kit; Task 2 adds `test_mass_assignment_points_to_input_types_in_both_practices`.
- A pasted snippet in Java or .NET that still answers without the practice loading. A person expects the practice to load; Task 1 widens `securing-code`'s description and Task 7's smoke measures it.
- Labelled illustrations that a reader still takes for the only way. Task 6 adds `test_every_file_with_code_says_it_is_an_illustration` on every practice file with a code fence.

---

### Task 1: `securing-code`: five principles, neutral wording, description

**Files:**
- Modify: `plugins/aidlc/skills/securing-code/SKILL.md`, `plugins/aidlc/skills/securing-code/references/security-checklist.md`, `scripts/routing_cases.json`
- Create: `scripts/test_practices.py`

**Interfaces:**
- Produces: `scripts/test_practices.py` with `read(rel)`, `practice(name)`, `section(body, heading)` and `class PracticesTest`; later tasks append inside it.

- [ ] **Step 1: Write the failing tests.** Create `scripts/test_practices.py`:

```python
"""Plan 16: the eight earlier practices are complete, general across stacks, and label their code as illustrations."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "aidlc" / "skills"
EARLIER = ("securing-code", "designing-apis", "reviewing-code", "debugging-failures", "migrating-safely",
           "building-user-interfaces", "adding-observability", "tuning-performance")


def read(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def practice(name: str) -> str:
    return read(f"plugins/aidlc/skills/{name}/SKILL.md")


def section(body: str, heading: str) -> str:
    start = body.index(heading)
    end = body.find(" ## ", start + len(heading))
    return body[start:] if end < 0 else body[start:end]


class PracticesTest(unittest.TestCase):
    def test_securing_code_covers_the_five_attack_classes(self):
        formats = section(practice("securing-code"), "### Untrusted formats and binding")
        for phrase in ("**Deserialization.**", "`ObjectInputStream`", "`BinaryFormatter`", "`pickle`",
                       "**XML.**", "external entities", "**Mass assignment.**", "input type that lists only",
                       "**Template injection.**", "pass the input as data to a fixed template",
                       "**Regular expressions (ReDoS).**", "nested quantifiers", "match timeout"):
            self.assertIn(phrase, formats)
        checklist = read("plugins/aidlc/skills/securing-code/references/security-checklist.md")
        for phrase in ("type-choosing deserializer", "DTDs and external entities are off",
                       "bound to an input type", "never built from user input", "length-capped"):
            self.assertIn(phrase, checklist)

    def test_securing_code_names_several_stacks_where_it_named_one(self):
        text = practice("securing-code")
        self.assertNotIn("(helmet or the framework equivalent)", text)
        self.assertIn("Spring Security", text)
        self.assertNotIn("`sameSite: 'lax'`", text)
        self.assertIn("SameSite=Lax or Strict (the CSRF defence", text)
        self.assertIn("the Maven or Gradle wrapper", text)
        self.assertIn("Sigstore attestations", text)

    def test_securing_code_description_names_the_new_triggers(self):
        body = (SKILLS / "securing-code/SKILL.md").read_text(encoding="utf-8")
        description = re.search(r"^description: (.*)$", body, re.M).group(1)
        self.assertLessEqual(len(description), 1024)
        for word in ("deserialises", "parses XML", "binds a request body", "template", "regular expression"):
            self.assertIn(word, description)
        cases = json.loads((ROOT / "scripts/routing_cases.json").read_text(encoding="utf-8"))
        prompts = [c["prompt"] for c in cases["securing-code"]["positive"]]
        self.assertIn("Is it safe to bind this request body straight onto the User entity?", prompts)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest scripts.test_practices 2>&1 | tail -1`
Expected: `FAILED (failures=3)`.

- [ ] **Step 3: Add the five principles.** In `securing-code/SKILL.md`, after the "### Input validation and uploads" block (it ends with the line "Patterns: [Schema validation](…), [File upload](…)."), add:

```markdown
### Untrusted formats and binding

Parsers, binders and template engines do more than read data. Configured loosely, they run code or exhaust the
server, so treat each one as an injection point.

- **Deserialization.** Never feed untrusted bytes to a deserializer that chooses which type to build: Java's
  `ObjectInputStream`, .NET's `BinaryFormatter`, Python's `pickle`, Ruby's `Marshal`, PHP's `unserialize`, or a JSON
  library with polymorphic typing switched on (Jackson's default typing, Json.NET's `TypeNameHandling`). Parse a
  plain data format into a fixed type instead. Where a native format cannot be avoided, allow only a listed set of
  classes (Java's `ObjectInputFilter`) (A08).
- **XML.** Switch off DTDs and external entities before parsing XML you did not write. An external entity can read
  local files or call internal hosts (XXE), and nested entities can exhaust memory. Java's `DocumentBuilderFactory`,
  SAX and StAX parsers need it set explicitly; .NET keeps `DtdProcessing.Prohibit` and no `XmlResolver`; Python's
  standard parsers are not hardened against every entity attack, and `defusedxml` closes the gap (adding it is a
  dependency decision).
- **Mass assignment.** Never bind a request body straight onto a stored entity: a client adds `isAdmin` or `ownerId`
  and the framework writes it. Bind to an input type that lists only the fields the client may set, then copy them
  across, on update as well as create: a DTO or record in Java and .NET, a Pydantic model or a Django REST framework
  serializer's `fields`, strong parameters in Rails (API3).
- **Template injection.** Never build a template from user input; pass the input as data to a fixed template.
  Server-side engines (Jinja2's `render_template_string`, Freemarker, Velocity, Thymeleaf expressions, Razor compiled
  at runtime, Handlebars) execute what the template says, so user text inside one is code execution. Where users must
  write templates, use a sandboxed, logic-less engine.
- **Regular expressions (ReDoS).** A pattern with nested or overlapping quantifiers (`(a+)+`, `(a|aa)*`) can take
  exponential time on a crafted input and hold a CPU per request. Cap the input's length before matching, keep
  nested quantifiers away from user input, and prefer a linear-time engine or a match timeout: RE2 or Go's `regexp`,
  Rust's `regex`, .NET's `Regex` with a `matchTimeout` or `RegexOptions.NonBacktracking`. Java's engine has no
  timeout, so bound the input there.
```

- [ ] **Step 4: Make the one-stack lines general.** In `securing-code/SKILL.md`:
  - Replace "- Security headers on every response (helmet or the framework equivalent); CSP starts from" with "- Security headers on every response, set once in the framework's middleware or filter (helmet in Express, Spring Security's header writers, ASP.NET Core middleware, Django's `SecurityMiddleware`); CSP starts from".
  - Replace "- Session cookies are `httpOnly`, `secure`, and `sameSite: 'lax'` or `'strict'` (the CSRF defense; `'none'` sends the cookie on cross-site requests), with a bounded `maxAge`." with "- Session cookies are HttpOnly, Secure and SameSite=Lax or Strict (the CSRF defence; None sends the cookie on cross-site requests), with a bounded lifetime."
  - Replace "Corroborate `packageManager` (when present), the lockfile, and CI;" with "Corroborate the declared tool version (`packageManager` in Node, the Maven or Gradle wrapper, `global.json` in .NET), the lockfile, and CI;".
  - Replace "**Check that dependency scripts are blocked before first execution.**" with "**Check that dependency scripts that run at install time (npm and pnpm lifecycle scripts, Python source builds) are blocked before first execution.**".
  - Replace "(`npm audit signatures`, `pnpm audit signatures`)" with "(`npm audit signatures`, Maven's signature check, NuGet's signed-package verification, Sigstore attestations where the registry publishes them)".
  - In `references/security-checklist.md`, replace "- [ ] Session cookies: `httpOnly`, `secure`, `sameSite: 'lax'`" with "- [ ] Session cookies: HttpOnly, Secure, SameSite=Lax or Strict".

- [ ] **Step 5: Add the checklist lines.** In `references/security-checklist.md`, after "- [ ] Destructive path operations (delete/move/overwrite): symlinks resolved, allowlisted root, minimum depth, ownership evidence read before the call", add:

```markdown
- [ ] No untrusted bytes reach a type-choosing deserializer (`ObjectInputStream`, `BinaryFormatter`, `pickle`, polymorphic JSON typing)
- [ ] XML from outside is parsed with DTDs and external entities are off
- [ ] Request bodies are bound to an input type that lists the settable fields, never to a stored entity
- [ ] Templates are never built from user input; input is passed as data
- [ ] Regular expressions on user input are length-capped and free of nested quantifiers, or run on a linear-time engine or with a timeout
```

- [ ] **Step 6: Widen the description and add a routing case.**
  - In the front matter's `description:`, after "or whether a file upload or an endpoint can be abused.", add " Use when code deserialises data, parses XML, binds a request body to an object, renders a template from input, or matches input with a regular expression."
  - In `scripts/routing_cases.json`, append to `securing-code`'s `positive` list: `{"prompt": "Is it safe to bind this request body straight onto the User entity?", "top_k": 3}`.

- [ ] **Step 7: Run all tests, the validator and the routing check.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | grep -E "^Ran|^OK|^FAILED"; python3 scripts/validate.py | tail -1; python3 scripts/route_check.py | tail -1`
Expected: `OK`; 0 problems; rank-1 at or above 85%, no misses, no wrong owners.

- [ ] **Step 8: Commit.**

```bash
git add plugins/aidlc/skills/securing-code scripts/test_practices.py scripts/routing_cases.json
git commit -m "feat(securing-code): deserialization, XXE, mass assignment, template injection and ReDoS; neutral wording

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `designing-apis` and `reviewing-code`

**Files:**
- Modify: `plugins/aidlc/skills/designing-apis/SKILL.md`, `plugins/aidlc/skills/reviewing-code/SKILL.md`
- Test: `scripts/test_practices.py`

- [ ] **Step 1: Write the failing tests.** Append inside `class PracticesTest`:

```python
    def test_designing_apis_gaps(self):
        text = practice("designing-apis")
        self.assertIn("adds a required field, tightens validation, or changes a default", section(text, "### 4. Prefer Addition"))
        self.assertIn("ignore unknown fields", text)
        self.assertIn("412 Precondition Failed", section(text, "### Partial Updates (PATCH)"))
        self.assertIn("RFC 9457", section(text, "### 2. Consistent Error Semantics"))
        self.assertIn("429", section(text, "### 2. Consistent Error Semantics"))
        self.assertIn("opaque next-page token", section(text, "### Pagination"))

    def test_designing_apis_is_general(self):
        text = practice("designing-apis")
        self.assertNotIn("## TypeScript Interface Patterns", text)
        self.assertIn("## Type Patterns (TypeScript shown)", text)
        self.assertIn("sealed interfaces", text)
        self.assertNotIn("The types ARE the documentation.", text)
        self.assertIn("The contract is the documentation", text)
        self.assertIn("Use one convention across the API", text)

    def test_reviewing_code_gaps(self):
        text = practice("reviewing-code")
        correctness = section(text, "### 1. Correctness")
        self.assertIn("old and new versions run side by side", correctness)
        self.assertIn("Does every call to another process have a timeout?", correctness)
        self.assertIn("Open the whole file, and the callers", section(text, "### Step 4: Review the Implementation"))

    def test_reviewing_code_is_general(self):
        text = practice("reviewing-code")
        self.assertIn("`interface{}` in Go", text)
        self.assertNotIn("(`npm audit`)", text)
        self.assertIn("`pip-audit`", text)
        self.assertNotIn("not just `package.json`", text)
        self.assertIn("not only the manifest", text)

    def test_mass_assignment_points_to_input_types_in_both_practices(self):
        self.assertIn("Input/Output Separation", practice("designing-apis"))
        self.assertIn("`securing-code` (mass assignment)", practice("designing-apis"))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 5 FAIL.

- [ ] **Step 3: Edit `designing-apis/SKILL.md`.**
  - In "### 2. Consistent Error Semantics", after its last paragraph (before "### 3. Validate at Boundaries"), add: "For HTTP APIs, prefer the standard Problem Details shape (RFC 9457, `application/problem+json`) to a home-made one, and carry your machine-readable code as an extension member. Many frameworks produce it already: ASP.NET Core's `AddProblemDetails`, Spring's `ProblemDetail`, and middleware for FastAPI and Express. Send 429 with `Retry-After` when a caller is throttled."
  - In "### 4. Prefer Addition Over Modification", after its last paragraph, add: "A change also breaks consumers when it adds a required field, tightens validation, or changes a default, a format or a field's meaning. Adding a value to a response enum is a change too: document it. Write consumers that ignore unknown fields and map unknown enum values to a fallback (Jackson with `FAIL_ON_UNKNOWN_PROPERTIES` off, System.Text.Json's default, Pydantic's `extra='ignore'`)."
  - Replace the rows "| Query params | camelCase | `?sortBy=createdAt&pageSize=20` |", "| Response fields | camelCase | `{ createdAt, updatedAt, taskId }` |" and "| Enum values | UPPER_SNAKE | `\"IN_PROGRESS\"`, `\"COMPLETED\"` |" by keeping each row and changing its Convention cell to "One convention across the API (camelCase shown)", and add after the table: "Use one convention across the API, the one it already uses; lowerCamelCase is the common default for new JSON."
  - In "### Pagination", after its code block, add: "Prefer an opaque next-page token to page numbers when the data changes or grows: offsets skip or repeat rows and slow down on deep pages. Cap the page size on the server. Treat a total count as optional, and say when it is an estimate."
  - In "### Partial Updates (PATCH)", after its code block, add: "Two clients that read, edit and write one resource silently overwrite each other. Return a version with each resource (an `ETag` or a version field), require it on updates (`If-Match`), and reject a stale one with 412 Precondition Failed (or 409). Most persistence layers enforce it: JPA's `@Version`, EF Core's concurrency tokens, or a `WHERE version = ?` clause in Go or Django."
  - In "### Resource Design", replace `/:id` with `/{id}` in the route block (the OpenAPI template form).
  - Replace "## TypeScript Interface Patterns" with "## Type Patterns (TypeScript shown)", and add under it: "The patterns hold in any typed stack: variants as sealed interfaces with records in Java, records in C#, Pydantic discriminated unions, a type switch in Go; typed IDs as a single-field record in Java or C#, `type TaskID string` in Go, `NewType` in Python."
  - In "### Input/Output Separation", after its code block, add: "A separate input type is also the defence against mass assignment: see `securing-code` (mass assignment)."
  - Replace "The types ARE the documentation. Define them first." with "The contract is the documentation: types, or an OpenAPI or protobuf schema. Define it first."

- [ ] **Step 4: Edit `reviewing-code/SKILL.md`.**
  - In "### 1. Correctness", add two bullets at its end:
    "- Is the change safe while old and new versions run side by side, and after a rollback? A change that writes a new data format, message shape or cache entry needs every reader deployed first (`migrating-safely`). A change that cannot be rolled back says so in its description."
    "- Does every call to another process have a timeout? Does it retry a bounded number of times, with backoff and jitter, and only for idempotent operations? Check the client's defaults, which are long or missing: .NET's `HttpClient` waits 100 seconds; Python's `requests`, Go's `http.DefaultClient` and Java's `HttpClient` set no request timeout."
  - In "### Step 4: Review the Implementation", add at its start: "Read every changed line. Open the whole file, and the callers of anything whose signature or behaviour changed. If a part is too hard to follow, ask the author before you go on."
  - Replace "Question gratuitous `any`/`unknown`/optional/casts" with "Question gratuitous escapes from the type system (`any` or `unknown` in TypeScript, raw types or `Object` in Java, `dynamic` in C#, `Any` in Python, `interface{}` in Go), optionals, casts".
  - Replace "- Any unnecessary re-renders in UI components?" with "- Any needless UI re-renders or recomputation?".
  - Replace "4. Does it have known vulnerabilities? (`npm audit`)" with "4. Does it have known vulnerabilities? (the ecosystem's audit: `npm audit`, `pip-audit`, `dotnet list package --vulnerable`, OWASP Dependency-Check, `govulncheck`)".
  - Replace "Review the lockfile diff, not just `package.json`;" with "Review the lockfile or the resolved tree (`package-lock.json`, `packages.lock.json`, `uv.lock`, `go.sum`; `mvn dependency:tree` where there is no lockfile), not only the manifest;".
  - Replace "For triaging `npm audit` findings" with "For triaging audit findings".

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.** `git add plugins/aidlc/skills/designing-apis plugins/aidlc/skills/reviewing-code scripts/test_practices.py`; message "feat(designing-apis,reviewing-code): breaking changes, concurrency, Problem Details, cursors; rollout safety, timeouts, whole-file reading; neutral wording" with the co-author line.

---

### Task 3: `debugging-failures` and `migrating-safely`

**Files:**
- Modify: `plugins/aidlc/skills/debugging-failures/SKILL.md`, `plugins/aidlc/skills/migrating-safely/SKILL.md`
- Test: `scripts/test_practices.py`

- [ ] **Step 1: Write the failing tests.** Append inside `class PracticesTest`:

```python
    def test_debugging_failures_gaps(self):
        text = practice("debugging-failures")
        localize = section(text, "### Step 2: Localize")
        self.assertIn("First ask what changed between the last good run and the first bad one", localize)
        self.assertIn("the observation that would disprove it", localize)
        self.assertIn("race or memory checker", text)
        self.assertIn("thread dump", text)

    def test_debugging_failures_is_general(self):
        text = practice("debugging-failures")
        for gone in ("Compare Node/browser versions", "Check package.json", "Check Node version",
                     "TypeError: Cannot read property 'x' of undefined"):
            self.assertNotIn(gone, text)
        self.assertIn("`NullPointerException`", text)
        self.assertIn("runtime or SDK version", text)

    def test_migrating_safely_gaps(self):
        text = practice("migrating-safely")
        rules = section(text, "### Database Schema Migrations (Expand/Contract)")
        self.assertIn("Set a short lock timeout and retry", rules)
        self.assertIn("Never edit or delete a migration once it has run", rules)
        self.assertIn("prove the copy", rules)
        self.assertIn("### Expand/Contract for Messages, Caches and Files", text)

    def test_migrating_safely_has_a_way_back_for_every_tool(self):
        text = practice("migrating-safely")
        self.assertNotIn("Write the `down` and run it before merging", text)
        self.assertIn("restore-from-backup or roll-forward procedure", text)
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 4 FAIL.

- [ ] **Step 3: Edit `debugging-failures/SKILL.md`.**
  - In "### Step 2: Localize", add at its start: "First ask what changed between the last good run and the first bad one: code, dependency versions, configuration, feature flags, data, the runtime image or the infrastructure. Compare the resolved dependencies (`package-lock.json`, `uv.lock`, `packages.lock.json`, `go.sum`, Maven's `dependency:tree`) as well as the commits. State each suspected cause as a hypothesis, with the observation that would disprove it. Test the likeliest first and change one thing per test. Record every result, including the ruled-out ones, in the progress note."
  - In the "When a bug can't be reproduced" tree, replace "Compare Node/browser versions, OS, environment variables" with "Compare runtime and SDK versions (Node, JDK, .NET SDK, Python, Go), OS, browser and environment variables". After the "Timing-dependent?" branch's lines, add a line in the same tree style: "│   ├── Run the failing path under the race or memory checker first (Go's -race, ThreadSanitizer or AddressSanitizer); for a hang, take a thread dump (jstack, dotnet-stack, py-spy dump)".
  - Replace "Dependency error → Check package.json; report" with "Dependency error → Check the manifest and lockfile; report".
  - Replace "Environment error → Check Node version, OS compatibility" with "Environment error → Check the runtime or SDK version, OS compatibility".
  - Replace "TypeError: Cannot read property 'x' of undefined" with "A null dereference (`TypeError` in JavaScript, `NullPointerException`, `NullReferenceException`, `AttributeError` on `None`, a nil pointer in Go)".
  - Replace "- Error boundaries that report errors" with "- The UI framework's error handler or boundary, reporting errors".

- [ ] **Step 4: Edit `migrating-safely/SKILL.md`.**
  - In the worked example under "### Database Schema Migrations (Expand/Contract)", between steps 3 and 4, add a step in the list's style: "Before switching reads, prove the copy: compare counts and sampled values, and run both reads side by side, logging differences. Keep the old column until every difference is explained." Renumber the following steps.
  - In its "**Rules:**" list, replace "- **Every migration has a tested down path.** A migration you can't reverse is a deploy you can't roll back. Write the `down` and run it before merging." with "- **Every migration has a rehearsed way back.** Use the tool's down or undo step where it has one (Alembic `downgrade`, EF Core `Down`, Liquibase `rollback`), and run it before merging. Where a step destroys data, or the tool has no down step, write and rehearse a restore-from-backup or roll-forward procedure instead."
  - Add to the same list:
    "- **Mind the lock.** Even a quick schema change waits for an exclusive lock, and every query behind it waits too. Set a short lock timeout and retry, and use the database's online forms: PostgreSQL's `lock_timeout` with `NOT VALID` then `VALIDATE CONSTRAINT`, MySQL's `ALGORITHM=INSTANT` or `LOCK=NONE`, SQL Server's `ONLINE = ON` for indexes."
    "- **Never edit or delete a migration once it has run on a shared database;** add a corrective one. The tool records what ran (Flyway checksums, Liquibase's `DATABASECHANGELOG`, EF Core's `__EFMigrationsHistory`, Alembic's version table)."
  - After the "### Database Schema Migrations (Expand/Contract)" block (before "## Zombie Code"), add:

```markdown
### Expand/Contract for Messages, Caches and Files

The same two steps apply to every shared format, not only tables: queue messages, cached values, files and API
payloads. Ship readers of the new format in one deploy and writers in a later one, so either deploy can roll back.
Version the data and keep unknown fields (protobuf, Avro with a registry compatibility check, JSON readers that
ignore unknown properties).
```

  - In "## Common Rationalizations", replace "A migration with no down path is a deploy you can't reverse. Write the `down` and run it before merging." with "A migration with no rehearsed way back is a deploy you can't reverse. Rehearse the down step, or the restore or roll-forward, before merging."

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.** `git add plugins/aidlc/skills/debugging-failures plugins/aidlc/skills/migrating-safely scripts/test_practices.py`; message "feat(debugging-failures,migrating-safely): what changed, hypotheses, detectors; locks, applied migrations, proven backfills, shared formats; a way back for every tool" with the co-author line.

---

### Task 4: `building-user-interfaces`: WCAG 2.2, internationalisation, user settings

**Files:**
- Modify: `plugins/aidlc/skills/building-user-interfaces/SKILL.md`, `plugins/aidlc/skills/building-user-interfaces/references/accessibility-checklist.md`
- Test: `scripts/test_practices.py`

- [ ] **Step 1: Write the failing tests.** Append inside `class PracticesTest`:

```python
    def test_ui_targets_wcag_2_2(self):
        text = practice("building-user-interfaces")
        checklist = read("plugins/aidlc/skills/building-user-interfaces/references/accessibility-checklist.md")
        for body in (text, checklist):
            self.assertNotIn("WCAG 2.1", body)
            self.assertIn("WCAG 2.2", body)
        self.assertIn("24 by 24 CSS pixels", text)
        self.assertNotIn("18px+", checklist)
        self.assertIn("18 pt, or 14 pt bold", checklist)
        self.assertNotIn("Touch targets ≥ 44x44px on mobile", checklist)

    def test_ui_gaps(self):
        text = practice("building-user-interfaces")
        self.assertIn("## Internationalisation", text)
        self.assertIn("resource catalogue", text)
        self.assertIn("start and end rather than left and right", text)
        self.assertIn("Honour the user's system settings for text size, reduced motion and contrast", text)

    def test_ui_is_general(self):
        text = practice("building-user-interfaces")
        self.assertIn("SwiftUI", section(text, "## State Management"))
        self.assertIn("`contentDescription` on Android", text)
        self.assertNotIn("no console errors", text)
        self.assertIn("browser console or device log", text)
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 3 FAIL.

- [ ] **Step 3: Edit `building-user-interfaces/SKILL.md`.**
  - Replace "## Accessibility (WCAG 2.1 AA)" with "## Accessibility (WCAG 2.2 AA)", and add under it: "Give every pointer target at least 24 by 24 CSS pixels, and never let a sticky header or banner hide the focused element. Offer a single-tap or keyboard route for anything that needs dragging. Let people paste and use a password manager at sign-in, and never ask twice in one flow for data they have already given."
  - In "## State Management", after the state block, add: "The same order holds in every UI stack: React hooks or TanStack Query, Angular signals or services, SwiftUI `@State` or `@Observable`, a Compose `ViewModel`."
  - In "### ARIA Labels", add at its start: "Give every control an accessible name: `aria-label` or `<label>` on the web, `accessibilityLabel` in SwiftUI and React Native, `contentDescription` on Android, `AutomationProperties.Name` in WPF and WinUI."
  - After the "## Responsive Design" section (before "## Loading and Transitions"), add:

```markdown
## Internationalisation

Keep every user-visible string in the platform's resource catalogue, and format dates, numbers, currency and plurals
through the locale APIs, never by hand. Build sentences from whole messages with placeholders, not joined fragments.
Lay out with start and end rather than left and right, and leave room for text to grow by a third. For example: ICU
MessageFormat or `Intl` on the web, `strings.xml` on Android, String Catalogs on iOS, `.resx` in .NET.
```

  - In "## Loading and Transitions", add at its start: "Honour the user's system settings for text size, reduced motion and contrast, and check the screen at the largest text size: `prefers-reduced-motion` and `rem` units on the web, Dynamic Type in SwiftUI, `sp` units and the animator scale on Android, high-contrast themes in WPF and WinUI."
  - Replace "Test at each of these breakpoints: 320px, 768px, 1024px, 1440px." with "Test at the smallest supported width (320 CSS px for web reflow), a tablet and a desktop size; on native, the smallest supported device at the largest text size."
  - In "## Verification": replace "- [ ] The component renders with no console errors" with "- [ ] The component renders with no runtime errors or warnings in the browser console or device log"; replace "(Tab through the page)" with "(with the keyboard alone, and with the platform's screen reader)"; replace "- [ ] Responsive: it works at 320px, 768px, 1024px, 1440px" with "- [ ] Responsive: it works at the smallest supported width, a tablet and a desktop size".

- [ ] **Step 4: Edit `references/accessibility-checklist.md`.**
  - Replace "WCAG 2.1 AA" with "WCAG 2.2 AA".
  - Replace "(large text, 18px+)" with "(large text: 18 pt, or 14 pt bold, about 24 or 18.7 CSS px)".
  - Replace "- [ ] Touch targets ≥ 44x44px on mobile" with "- [ ] Pointer targets at least 24 by 24 CSS px (AA, 2.5.8); 44 by 44 is the stricter AAA level".
  - Add after that line: "- [ ] The focused element is never hidden by a sticky header or banner (2.4.11)", "- [ ] Anything dragged has a single-pointer alternative (2.5.7)", "- [ ] Sign-in allows paste and password managers (3.3.8); a flow never asks twice for the same data (3.3.7)".

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.** `git add plugins/aidlc/skills/building-user-interfaces scripts/test_practices.py`; message "feat(building-user-interfaces): WCAG 2.2, internationalisation, user settings; neutral wording" with the co-author line.

---

### Task 5: `adding-observability` and `tuning-performance`

**Files:**
- Modify: `plugins/aidlc/skills/adding-observability/SKILL.md`, `plugins/aidlc/skills/adding-observability/references/observability-checklist.md`, `plugins/aidlc/skills/tuning-performance/SKILL.md`, `plugins/aidlc/skills/tuning-performance/references/performance-checklist.md`
- Test: `scripts/test_practices.py`

- [ ] **Step 1: Write the failing tests.** Append inside `class PracticesTest`:

```python
    def test_observability_gaps(self):
        text = practice("adding-observability")
        self.assertIn("alert on how fast the error budget is burning", section(text, "### 6. Alerting"))
        self.assertIn("W3C Trace Context as the correlation ID", section(text, "### 3. Structured logging"))
        self.assertIn("OpenTelemetry semantic conventions", section(text, "### 4. Metrics"))
        self.assertIn("`service.version`", text)
        self.assertIn("shutdown or flush before a short-lived process exits", section(text, "### 5. Distributed tracing"))

    def test_observability_is_current_and_general(self):
        text = practice("adding-observability")
        checklist = read("plugins/aidlc/skills/adding-observability/references/observability-checklist.md")
        self.assertNotIn("grouped by class (`5xx`, not `503`)", checklist)
        self.assertIn("`-javaagent`", section(text, "### 5. Distributed tracing"))
        self.assertNotIn("\"console.log is fine for now\"", text)

    def test_performance_gaps(self):
        text = practice("tuning-performance")
        measure = section(text, "### Step 1: Measure")
        self.assertIn("sampling profiler", measure)
        self.assertIn("production-like concurrency", measure)
        self.assertIn("benchmark harness", section(text, "### Step 4: Verify"))
        self.assertIn("cold-start time", text)

    def test_performance_is_current_and_general(self):
        text = practice("tuning-performance")
        checklist = read("plugins/aidlc/skills/tuning-performance/references/performance-checklist.md")
        self.assertNotIn("Time to Interactive", text)
        self.assertNotIn("Time to Interactive", checklist)
        self.assertNotIn("`isInputPending()` to yield only when needed", checklist)
        self.assertIn("SQL Server", text)
        self.assertIn("`OnPush`", text)
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 4 FAIL.

- [ ] **Step 3: Edit `adding-observability/SKILL.md`.**
  - In "### 3. Structured logging", after the paragraph beginning "**Correlation IDs are mandatory.**", add: "Use the W3C Trace Context as the correlation ID rather than a second scheme, and put the trace and span IDs on every log record through the logging library's OpenTelemetry bridge: the Java agent's Logback or Log4j appender, the OpenTelemetry provider for .NET's `ILogger`, the Python logging handler, the `otelslog` bridge in Go. Accept or create the context in the framework's inbound middleware or filter (a servlet filter, ASP.NET Core middleware, a WSGI or ASGI middleware, an `http.Handler` wrapper); the Express code below is one illustration."
  - In "### 4. Metrics", after its first paragraph, add: "Name attributes and metrics with the OpenTelemetry semantic conventions (`http.server.request.duration`, `http.route`, `http.response.status_code`) instead of inventing names; the exact status code is a bounded set. Set `service.name`, `service.version` and the deployment environment as resource attributes, so every signal can be traced to a release."
  - In "### 5. Distributed tracing", add at its start: "Start the SDK before the code it instruments loads: a preloaded module in Node, `-javaagent` for Java, the auto-instrumentation or `AddOpenTelemetry` at host build in .NET, `opentelemetry-instrument` in Python; Go has no agent, so wrap handlers and clients explicitly. Export in the background so telemetry never blocks a request, and call the SDK's shutdown or flush before a short-lived process exits (jobs, CLIs, serverless handlers, workers)."
  - In "### 6. Alerting", add at its start: "Define each user-facing indicator and its SLO first, then alert on how fast the error budget is burning rather than on a raw threshold. Page when both a long and a short window burn fast (for example 14.4 times the sustainable rate over one hour and over five minutes), and open a ticket for a slow burn over days."
  - In "## Common Rationalizations", replace "| \"console.log is fine for now\" |" with "| \"Printing to stdout is fine for now\" |".
  - In `references/observability-checklist.md`, replace "- [ ] Status codes grouped by class (`5xx`, not `503`)" with "- [ ] HTTP status recorded as the exact code (`http.response.status_code`), a bounded set; high-cardinality values such as IDs and raw paths never become labels".

- [ ] **Step 4: Edit `tuning-performance/SKILL.md`.**
  - In "### Step 1: Measure", after the "**Backend:**" code block, add: "Find hotspots with a sampling profiler and read the flame graph rather than timing calls by hand: JFR or async-profiler for Java, `dotnet-trace` and `dotnet-counters` for .NET, `py-spy` for Python, `pprof` for Go, `--cpu-prof` for Node. For a backend change, also measure p95 and p99 at production-like concurrency and data volume (k6, Gatling, JMeter or Locust against a staging copy), and find where latency turns sharply upwards before users do."
  - In "## Core Web Vitals Targets", add at its end: "For web pages, these are the targets. For native apps, track the platform's own measures instead: cold-start time, slow and frozen frames, hangs or ANRs, and memory (Android vitals, Xcode Organizer or MetricKit on iOS)."
  - In "### Step 4: Verify (Keep or Revert)", add at its start: "Measure a small hot path with the platform's benchmark harness, which handles warm-up and keeps the compiler from deleting the work: JMH for Java, BenchmarkDotNet for .NET, `testing.B` for Go, `pyperf` for Python."
  - Replace "\"Add an index\" is a guess; `EXPLAIN ANALYZE` is the measurement." with "\"Add an index\" is a guess; the actual execution plan is the measurement (`EXPLAIN ANALYZE` in PostgreSQL and MySQL, the actual execution plan in SQL Server, `DBMS_XPLAN` in Oracle; PostgreSQL shown below)."
  - Replace "Reserve `React.memo` and `useMemo` for work the profile" with "Skip re-rendering UI whose inputs did not change (`memo` in React, `OnPush` or signals in Angular, stable parameters in Compose, `Equatable` views in SwiftUI), and reserve it for work the profile".
  - Replace "The real gains are route-level code splitting and lazy-loading heavy, rarely-used features behind `Suspense`." with "The real gains are shipping less code on first load: route-level splitting and lazy loading on the web (`Suspense` in React), dynamic feature modules on Android, trimming or AOT in .NET."
  - Replace the line "Time to Interactive: < 3.5s on 4G" with "Total Blocking Time: < 200ms (lab)".
  - Replace "- [ ] Core Web Vitals are within \"Good\" thresholds" with "- [ ] Web pages: Core Web Vitals are within \"Good\" thresholds; native clients: startup and frame budgets are met".
  - In `references/performance-checklist.md`, replace ", `isInputPending()` to yield only when needed" with "; yield regularly rather than checking `isInputPending()`, which is no longer recommended", and replace "| Large bundles | Slow Time to Interactive |" with "| Large bundles | Slow LCP and high Total Blocking Time |".

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.** `git add plugins/aidlc/skills/adding-observability plugins/aidlc/skills/tuning-performance scripts/test_practices.py`; message "feat(adding-observability,tuning-performance): SLO burn rates, trace-correlated logs, semantic conventions, flush; profilers, load tests, harnesses, native budgets; current metrics" with the co-author line.

---

### Task 6: Code is labelled as illustration

**Files:**
- Modify: every `SKILL.md` of the eight practices and every file in their `references/` that holds a code fence
- Test: `scripts/test_practices.py`

- [ ] **Step 1: Write the failing test.** Append inside `class PracticesTest`:

```python
    def test_every_file_with_code_says_it_is_an_illustration(self):
        missing = []
        for name in EARLIER:
            for path in [SKILLS / name / "SKILL.md", *sorted((SKILLS / name).glob("references/*.md"))]:
                text = path.read_text(encoding="utf-8")
                if "```" in text and "is an illustration in one stack" not in text:
                    missing.append(str(path.relative_to(ROOT)))
        self.assertEqual(missing, [])
```

- [ ] **Step 2: Run it and watch it fail.** Expected: 1 FAIL listing the files.

- [ ] **Step 3: Add the line.** In each listed `SKILL.md`, add after the first paragraph of "## Overview": "> Code in this skill is an illustration in one stack, mostly TypeScript; the rule in the text applies in every stack." In each listed reference file, add after its title line: "> Code in this file is an illustration in one stack; the rule in the skill applies in every stack." Also retag the three blocks in `accessibility-checklist.md` that hold JSX but say `html` as `jsx`, and the two blocks in `designing-apis` that hold HTTP and JSON but say `typescript` as `http`.

- [ ] **Step 4: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 5: Commit.** `git add plugins/aidlc/skills scripts/test_practices.py`; message "docs(practices): code is labelled as an illustration in one stack" with the co-author line.

---

### Task 7: Language cases, smoke, release aidlc 4.4.0 and the verification record

**Files:**
- Create: `plugins/aidlc/evals/language-java-xxe/`, `plugins/aidlc/evals/language-python-template-injection/` (each `prompt.md` and `graders/`, like `language-java-deserialization`)
- Modify: `plugins/aidlc/evals/README.md`, `plugins/aidlc/.claude-plugin/plugin.json`, `scripts/test_practices.py`
- Create: `docs/verification/2026-11-08-plan-16-practice-completeness.md`

- [ ] **Step 1: Write the failing test.** Append inside `class PracticesTest`:

```python
    def test_the_new_principles_have_language_cases(self):
        evals = ROOT / "plugins/aidlc/evals"
        for name in ("language-java-xxe", "language-python-template-injection"):
            self.assertTrue((evals / name / "prompt.md").is_file(), name)
            self.assertTrue((evals / name / "graders/fired.md").is_file(), name)
        self.assertIn("there are 30 cases", read("plugins/aidlc/evals/README.md"))
```

- [ ] **Step 2: Run it and watch it fail.** Expected: 1 FAIL.

- [ ] **Step 3: Write the two cases** in `language-java-deserialization`'s layout (front matter `tags: [language]`, `max_turns: 15`, `timeout_seconds: 300`, `allowed_tools: [Read, Glob, Grep, Skill]`; `graders/fired.md` identical to that case's; `graders/finds-it.md` an `llm` grader).
  - `language-java-xxe/prompt.md`: a Spring `@PostMapping("/shipments/import")` method that takes the raw request body as an `InputStream`, builds `DocumentBuilderFactory.newInstance().newDocumentBuilder()` with no features set, parses it, and reads `getElementsByTagName("reference")`; then "Is this import endpoint safe?". `finds-it.md`: "PASS if the reply identifies XML external entity (XXE) processing as the main risk and fixes it by disabling DTDs or external entities (for example the disallow-doctype-decl feature). FAIL otherwise."
  - `language-python-template-injection/prompt.md`: a Flask route `@app.route("/greet")` that reads `name = request.args.get("name", "")` and returns `render_template_string("<h1>Hello " + name + "</h1>")`; then "Anything wrong with this route?". `finds-it.md`: "PASS if the reply identifies server-side template injection (user input built into the template) as the main risk and passes the input as data to a fixed template instead. FAIL if it only mentions cross-site scripting."
  - README: replace "there are 28 cases" with "there are 30 cases".

- [ ] **Step 4: Version.** In `plugin.json`, replace `"version": "4.3.0"` with `"version": "4.4.0"`.

- [ ] **Step 5: Run every check.**

```bash
python3 scripts/validate.py | tail -1
python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3
python3 scripts/route_check.py | tail -3
claude plugin validate .
```

Expected: 0 problems; `OK` (304 plus Plan 16's tests); rank-1 at or above 85%; `Validation passed`.

- [ ] **Step 6: Commit.** `git add plugins/aidlc scripts/test_practices.py`; message "test(evals): Java XXE and Python template injection; aidlc 4.4.0" with the co-author line.

- [ ] **Step 7: Final review.** A fresh reviewer on the most capable model reads the whole branch against the spec's Plan 16 section, this plan's Research and decisions, and the Review Focus above, and checks every named API and default against current documentation. Fix critical, important and cheap real low findings test-first; dismiss other lows with a reason.

- [ ] **Step 8: Smoke, within the owner's cap** (about $2.50). Run the five language cases and the two Plan 15 cases still waiting, one at a time:

```bash
for c in language-java-deserialization language-dotnet-mass-assignment language-java-test-first \
         language-java-xxe language-python-template-injection route-f0-start gate-f0-data-change; do
  claude plugin eval plugins/aidlc --trust-plugin --scaffold --allow-tools Write Edit --no-publish --runs 1 \
    --ablation none --max-cost-usd <cap per case> --case "$c"
done
```

A miss on a principle is fixed in the principle, never in a grader; a practice that did not load is recorded as a finding.

- [ ] **Step 9: Write the verification record** in Plan 15's layout: the checks; the Research table; each gap added and each outdated statement fixed, per practice; the Review Focus cases; the smoke scores and spend; the review's findings and fixes; and the decisions. Commit it with the fix pass.
