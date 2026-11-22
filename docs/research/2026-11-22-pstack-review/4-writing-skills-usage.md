# pstack: how the eight writing and explaining skills are used

Source: GitHub `cursor/plugins`, folder `pstack`, version 0.15.46 (`pstack/plugin.json`), main at `7a58391` (2026-11-22); the last commit touching `pstack/` is `0b46ec3` (2026-11-19). Every Markdown, JSON and text file under `pstack/` was fetched to `scratchpad/pstack-gh/tree/pstack/` and searched there. Paths below are relative to `pstack/`.

Local copies: `scratchpad/pstack/<skill>.md` for all eight skills and the eight files in `scratchpad/pstack-pb/` (seven playbooks and `worker.md`) are byte-identical to GitHub. They do not differ.

## Summary

| skill | disable-model-invocation | documented use | called from (steps that tell the agent to use it) | verdict |
|---|---|---|---|---|
| `bro` | true | Typed by a person: `/bro` restates the last reply in plain words (README:158, docs/guide/10:148-151, poteto-help:87) | None. `ketchup/SKILL.md:11` borrows its voice only ("Use `/bro`'s voice, not its task") | Person only |
| `in-your-own-words` | true | Typed by a person; README:128 says "runs only when you type `/in-your-own-words`" | `interrogate/SKILL.md:13` (state the intent with it) | Mostly a person; one step in `interrogate` |
| `why` | true | Typed by a person (`/why ...`, README:131, :192); README:111 also lists it among the skills poteto-mode "runs ... for you when a step needs them" | `poteto-mode/playbooks/investigation.md:7`, `playbooks/bug-fix.md:8`, `teach/SKILL.md:11,14`, `agents/comment-sicko.md:26` (used by `no-comments`); dormant benny pack: `triage-issue-reports:71`, `reproduce-and-fix-issues:161` | Mix: a person and named steps |
| `how` | true | Typed by a person (`/how ...`, README:114, :130, :191). Not in README:111's poteto-mode list | `teach/SKILL.md:11,14` only | Mostly a person; called only by `teach` |
| `unslop` | true | Both. A person: "you're cleaning up writing" (README:157, guide/05:61-67). poteto-mode: "writes unslopped replies" (README:101) and README:111 list | `poteto-mode/SKILL.md:23` (all prose, every reply), `playbooks/investigation.md:10`, `technical-writing/SKILL.md:67`, `teach/SKILL.md:19`, `recall/SKILL.md:33`, `show-me-your-work/SKILL.md:36`, `automate-me/SKILL.md:3,11,77`, `blast-radius/SKILL.md:48`; benny pack (3 files) | Mostly called by other skills; also typed directly |
| `technical-writing` | true | Both. A person (README:159, guide/09:64-72, guide/04:93 "Name `/technical-writing` when the doc itself matters"); README:111 list | `poteto-mode/SKILL.md:23` (docs, PR descriptions, commit messages) only | Mix: one poteto-mode trigger and direct use |
| `teach` | true | Typed by a person (README:145, guide/03:37-48, poteto-help:73, recipes:13,29) | None | Person only (it calls `how`, `why` and `unslop` itself) |
| `ketchup` | true | Typed by a person (README:133, guide/07:70, guide/10:156-159, poteto-help:75) | `poteto-mode/playbooks/autopilot-full.md:22` (each loop tick that changed something) and `:25` (the Reply); `ketchup-video/SKILL.md:9` ("Follow `/ketchup`") | Mostly a person; called by one playbook and by `ketchup-video` |

No skill of the eight is model-invocable. None is triggered by its description alone.

## Key finding: the flag does not separate "person only" from "called by steps"

`disable-model-invocation: true` is set on 57 of pstack's 58 skills. Only `setup-pstack` lacks it. The flag is on the principle skills and on `architect`, `swarm`, `interrogate` and `tdd`, which poteto-mode routes to all the time. So the flag tells you nothing about which skills are user-facing.

pstack calls a flagged skill from a step by having the agent read its file, not by the model's skill trigger:

- `skills/poteto-mode/SKILL.md:11`: "Bundled skills live at `../<name>/SKILL.md` from this file, so put this file's absolute path in every `poteto-agent` prompt."
- `skills/poteto-mode/SKILL.md:20`: "The operator's rules live in skills that only load from a slash command, so they reach another agent no other way." (This is why subagents get `worker.md`.)
- `skills/automate-me/SKILL.md:73`: a generated `-mode` skill gets "Frontmatter `disable-model-invocation: true` by default."

So the answer for each skill comes from step 2, the steps that name it.

Note for aidlc: in Claude Code, `disable-model-invocation: true` also stops Claude from loading the skill through its Skill tool. An aidlc stage step that says "Load the `<name>` skill" may not reach a skill with that flag. pstack avoids this by pointing at the file path. Check this against the Claude Code skills documentation before copying the flag.

## Step 1: documentation

### README

- README:95-101 (poteto-mode): "when invoked it: 1. matches your task to a playbook ... 2. routes to the other skills as the steps fire. 3. writes unslopped replies framed for the consumer and the maintainer."
- README:111: "`/poteto-mode` runs most of these for you when a step needs them (`why`, `architect`, `arena`, `swarm`, `interrogate`, `unslop`, `no-comments`, `technical-writing`, `tdd`, and the principles). the table below is for when you want one directly". Of the eight, only `why`, `unslop` and `technical-writing` are on this list.
- README:128: "`/in-your-own-words` | you want the agent to play back your goal and the problem before it starts. runs only when you type `/in-your-own-words`."
- README:130: "`/how` | you want a walkthrough of how a subsystem works."
- README:131: "`/why` | you want to know why something was built this way. answers from the record, not the code ..."
- README:133: "`/ketchup` | you want what changed in this chat since your last message, in plain words and small visuals ..."
- README:145: "`/teach` | you want to actually understand a change or subsystem, not just have it summarized. runs how + why and weaves one plain explanation, built up diagram by diagram."
- README:157: "`/unslop` | you're cleaning up writing. removes AI tells."
- README:158: "`/bro` | you want the last message restated in plain human language, no jargon."
- README:159: "`/technical-writing` | layered doc standard (Diátaxis + Google developer style + STE + Global English) for docs, RFCs, readmes, PR descriptions, commit messages."
- README:167: "mostly i type `/poteto-mode` at the start of a task and let it route to a playbook. the other skills fire as the steps need them. a few i reach for directly."
- README:191-201 examples: `/how do we cancel runs? ...`, `/why is this feature flag not on yet?`, `unslop: can we unslop and tighten the new changes?`

### Front matter (each `skills/<name>/SKILL.md`, lines 2-4)

| skill | description | flag |
|---|---|---|
| bro | "Restate the last message in plain human language, with no jargon." | true |
| in-your-own-words | "Restate in your own words what you think the user's goals are and what problem they're trying to solve. Use for /in-your-own-words." | true |
| why | "Use for 'why does X work this way', 'why we picked Y', design rationale, regressions, postmortems, or data-backed thresholds. Returns a cited read on decisions and tradeoffs. Use how for runtime behavior." | true |
| how | "Use for \"how does X work\", code walkthroughs before changing something, and placement / ownership / layering questions ... Use why for motivation." | true |
| unslop | "Cut AI tells from any writing." | true |
| technical-writing | "Layered technical-writing standard ... Use for /technical-writing or when writing or reviewing docs, RFCs, readmes, PR descriptions, or commit messages." | true |
| teach | "Explain a body of work plainly so a person actually understands it. Runs the `how` and `why` skills ... Use for 'teach me this', 'help me really understand X', 'explain this change or subsystem to me'." | true |
| ketchup | "Catch the user up on what changed in this chat since their last message ... Use for /ketchup." | true |

None has an "invoked by" note. The "Use for /<name>" wording in four descriptions (in-your-own-words, technical-writing, ketchup, and the slash form in poteto-help) points at a person typing the command.

### poteto-help (the routing table for people)

`skills/poteto-help/SKILL.md` maps a person's goal to a slash command:
- :69 "Check that the agent understood their goal and the problem before it starts | `/in-your-own-words`"
- :71 "Know how code works now, or where new code should live | `/how`"
- :72 "Know why code is shaped this way, or where a number came from | `/why`"
- :73 "Understand a change or subsystem, explained plainly | `/teach`"
- :75 "Catch up on what changed in this chat ... | `/ketchup`"
- :85 "Clean AI tells out of prose | `/unslop`"
- :86 "Write docs, an RFC, a README, a PR description, or a commit message to a standard | `/technical-writing`"
- :87 "Hear the last reply again in plain words | `/bro`"
- :107 "`/how` explains what the code does. `/why` explains the reasons. `/teach` runs one or both and explains the result plainly."

`skills/poteto-help/references/recipes.md`: :8 `/in-your-own-words <long or messy ask>`; :11 `use /how to understand <subsystem>. then use /why ...`; :13 `/teach me why you implemented it this way ...`; :47 "`/ketchup` catches you up ..."; :51 "`/bro` restates the last reply in plain words."

### The guide (`docs/guide/`)

- 02-poteto-mode.md:67: "For the restatement alone, with no playbook, run `/in-your-own-words`." (poteto-mode's own first-message rule already restates the goal; the skill is the standalone version.)
- 03-understand.md:5: "pstack gives you four ways in. `/how` ... `/why` ... `/teach` blends both into one explanation. `/recall` ..."
- 03-understand.md:17: the Investigation playbook "traces the code, adds `/why` for questions about motivation".
- 03-understand.md:43: "`/teach` ... runs `/how` and `/why`, for a small change maybe just one of them".
- 04-design.md:93: "Name `/technical-writing` when the doc itself matters".
- 05-build-and-clean.md:59: "poteto-mode applies `/unslop` to the PR description and commit bodies." :64 `/unslop the readme changes, no emdashes`.
- 07-overnight.md:70: "For a quick status instead of an audit, run `/ketchup` in the chat that ran the work."
- 09-make-it-yours.md:64-72: "Write docs to a standard with `/technical-writing`", example `/technical-writing review the readme changes`.
- 10-recipes-and-pitfalls.md:21 (`/in-your-own-words`), :140 (`/unslop that, no emdashes`), :148-151 (`/bro`: "That's the whole prompt ... Use it when a reply is technically thorough and you still don't know what it said."), :156-161 (`/ketchup`, `/ketchup-video`).

Step 1 settles `bro` and `teach` (person only, and step 2 found no caller). It does not settle the other six: README:111 says poteto-mode runs `why`, `unslop` and `technical-writing`, and the other three could still be named in steps.

## Step 2: every place a skill or playbook names one of the eight

Search: whole-word `bro|in-your-own-words|unslop|technical-writing|teach|ketchup`, and for `why`/`how` the forms `**why**`, `` `why` ``, `/why`, "why skill", `skills/why` (same for how). README and each skill's own front matter excluded. Classification: **instruction** (use it at this step), **mention** (points a person to it, or names it as related), **description**.

### bro
- `skills/ketchup/SKILL.md:11`: "Use [`/bro`](../bro/SKILL.md)'s voice, not its task: plain words, short sentences, no jargon, like one person catching up another." **Style reference**, not a call. ketchup borrows bro's voice and says not to do bro's task.
- `skills/poteto-help/SKILL.md:87`, `references/recipes.md:51`, `docs/guide/10:148-151`: **mentions** for people.

### in-your-own-words
- `skills/interrogate/SKILL.md:13`: "State the intent with the **in-your-own-words** skill, from the user's message, the commits, and the PR description. Ask the user when the intent is unclear." **Instruction** at interrogate's scoping step.
- `skills/poteto-help/SKILL.md:69`, `references/recipes.md:8`, `docs/guide/02:67`, `docs/guide/10:21`: **mentions**.
- Related but unnamed: `skills/poteto-mode/SKILL.md:19`: "First message → restate the user's goal and the smallest change that meets it, then proceed." poteto-mode does the same thing inline without naming the skill.

### why
- `skills/poteto-mode/playbooks/investigation.md:7`: "Trace the code the question is about. For motivation questions, also route through the **why** skill." **Instruction**.
- `skills/poteto-mode/playbooks/bug-fix.md:8`: "Seed them with a trace of the affected subsystem and the **why** skill for regression history." **Instruction**.
- `skills/teach/SKILL.md:11`: "run `how` for how it works and `why` for why it's that way. Those are real skill invocations that do their own digging." **Instruction**.
- `skills/teach/SKILL.md:14`: "Read the code yourself to get oriented, then run `how` for how it works and `why` for why. Run them in parallel and combine the results." **Instruction**.
- `skills/teach/SKILL.md:21`: "the threads worth chasing with `how` or `why`." **Mention** (suggests follow-ups to the person).
- `agents/comment-sicko.md:26`: "I trace the named symbol or call, run `/why` from the **why** skill on it, or both." **Instruction** (the reviewer agent that `no-comments` spawns).
- `skills/blast-radius/SKILL.md:11`: "Companion to `how` and `why`. `how` tells you what the code does. `why` tells you why it's shaped that way." **Description**.
- `skills/poteto-help/SKILL.md:72,107`, `references/prompting.md:23`, `references/recipes.md:11`, `docs/guide/03:5,17,27-33`, `docs/guide/10:10`: **mentions**.
- Dormant benny pack: `automations/benny/skills/triage-issue-reports/SKILL.md:71` "Use pstack's `why` skill when the report looks like a regression or touches defensive code." and `reproduce-and-fix-issues/SKILL.md:161` "Use pstack's `why` skill for regression history and defensive code." **Instructions**. `setup-benny/SKILL.md:50` and `FOR_AGENTS.md:32,79` list it as a dependency. README:284 says the benny files "are not registered as slash skills".

### how
- `skills/teach/SKILL.md:11,14`: as above. **Instructions**.
- `skills/teach/SKILL.md:21`: **mention**.
- `skills/blast-radius/SKILL.md:11`: **description**.
- `skills/poteto-help/SKILL.md:48,71,107`, `references/prompting.md:23`, `references/recipes.md:11`, `docs/guide/03:5,19-25,77`, `docs/guide/10:10`: **mentions**.
- Not named in poteto-mode, any playbook, `worker.md` or `references/bugbot-triage.md`. Investigation step 1 says "Trace the code", which is `how`'s job, but does not name `how`.

### unslop
- `skills/poteto-mode/SKILL.md:23`: "Prose, your reply included → **unslop**. Docs, PR descriptions, commit messages → **technical-writing**." **Instruction** (a standing trigger for every reply).
- `skills/poteto-mode/playbooks/investigation.md:10`: "4. Apply the **unslop** skill to the reply." **Instruction**.
- `skills/technical-writing/SKILL.md:67`: "Apply the **unslop** skill to every doc this skill touches. That skill owns the slop-pattern catalog: AI vocabulary, filler, hedging, formatting tells." **Instruction**.
- `skills/teach/SKILL.md:19`: "Write every response through the **unslop** skill, in plain spoken English ..." **Instruction**.
- `skills/recall/SKILL.md:33`: "Write the brief through the **unslop** skill ..." **Instruction**.
- `skills/show-me-your-work/SKILL.md:36`: "(the **unslop** skill applies to log text too)." **Instruction**.
- `skills/automate-me/SKILL.md:3` (description: "via create-skill + unslop"), `:11` ("This skill orchestrates three others: ... and the **unslop** skill (prose discipline)"), `:77` ("Apply the **unslop** skill and `create-skill`'s writing guidelines to every line."). **Instructions**.
- `skills/blast-radius/SKILL.md:48`: "Write it through `unslop`, cite real code ..." **Instruction**.
- `skills/unslop/SKILL.md:11`: "Rule numbers are stable ids that other skills cite. A removed rule leaves a gap." **Description** (unslop is built to be cited).
- Benny pack: `triage-issue-reports/SKILL.md:28`, `setup-benny/SKILL.md:52,115`, `reproduce-and-fix-issues/SKILL.md:295`. **Instructions** (dormant pack).
- `plugin.json:19`, `.cursor-plugin/plugin.json:20`: listed as a keyword.
- `skills/poteto-help/SKILL.md:85`, `docs/guide/05:59-79`, `docs/guide/10:140`: **mentions**.

### technical-writing
- `skills/poteto-mode/SKILL.md:23`: "Docs, PR descriptions, commit messages → **technical-writing**." **Instruction**.
- No playbook names it. `playbooks/opening-a-pr.md` does not name it (the guide's 05:59 says poteto-mode applies `/unslop` to PR text).
- `skills/poteto-help/SKILL.md:86`, `docs/guide/04:93`, `docs/guide/09:64-72`: **mentions**.

### teach
- No skill, playbook, agent or `worker.md` tells the agent to run `teach`.
- `skills/poteto-help/SKILL.md:48,73`, `references/prompting.md:24`, `references/recipes.md:13,29`, `docs/guide/03:5,37-48`, `docs/guide/04:90`: **mentions** for people. recipes:29 and guide/04:90 chain it after a poteto-mode run in a person's prompt: "`/poteto-mode write a tutorial ... then /teach me why it beats the current one.`"

### ketchup
- `skills/poteto-mode/playbooks/autopilot-full.md:22` (step 6, the `/loop 1h` audit): "A tick that changed something for the operator ends by catching them up per the **ketchup** skill, and one that changed nothing stays quiet". **Instruction**.
- `skills/poteto-mode/playbooks/autopilot-full.md:25`: "**Reply:** catch the operator up per the **ketchup** skill, covering each PR's state and verdict, what merged, countersigns and why, open operator gates, and parked follow-ups ..." **Instruction**.
- `skills/ketchup-video/SKILL.md:9`: "Follow [`/ketchup`](../ketchup/SKILL.md), but show what happened in a short subtitled video instead of its summary and visuals." **Instruction** (ketchup-video is a variant built on it).
- `skills/poteto-help/SKILL.md:75,76,110`, `references/recipes.md:47`, `docs/guide/07:70`, `docs/guide/10:156-161`: **mentions**.
- Not named in `autonomous-run.md`, `autopilot-stack.md`, `babysit.md` or `worker.md`.

## Step 3: verdicts

- **bro**: called individually by a person only. Its voice is reused by `ketchup`.
- **in-your-own-words**: a person, plus one named step (`interrogate/SKILL.md:13`). poteto-mode does the same restatement inline on the first message without naming it.
- **why**: a mix. A person types it, and named steps call it: Investigation step 1, Bug fix step 2, `teach` steps 2 and the intro, and the Comment Sicko agent.
- **how**: a person, plus one caller, `teach`. No poteto-mode playbook names it.
- **unslop**: a mix, weighted to calls from others. poteto-mode applies it to all prose and every reply, and seven other skills plus the Investigation playbook name it. A person also types it to clean a target.
- **technical-writing**: a mix. One poteto-mode standing trigger (docs, PR descriptions, commit messages), and a person types it.
- **teach**: called individually by a person only. It is itself an orchestrator of `how`, `why` and `unslop`.
- **ketchup**: a person, plus the Autopilot-full playbook (each audit tick and the final reply) and `ketchup-video`.
- None is called by the AI on its own from its description: all eight set `disable-model-invocation: true`.

## pstack's own grouping signals

- **unslop is the base layer for all writing.** It references no other skill. Its rules carry "stable ids that other skills cite" (`unslop/SKILL.md:11`). `technical-writing` defers to it: "That skill owns the slop-pattern catalog" (`technical-writing/SKILL.md:67`). `teach`, `recall`, `show-me-your-work`, `automate-me` and `blast-radius` write "through" it. pstack keeps unslop (prose hygiene) and technical-writing (document standard) as two skills, with technical-writing on top.
- **teach is built on how and why.** "Teach sits on top of `how` and `why` ... Those are real skill invocations that do their own digging" (`teach/SKILL.md:11`). It also writes through unslop (:19). It does not reference bro or technical-writing.
- **how and why point at each other.** Their descriptions split the ground: `why` says "Use how for runtime behavior"; `how` says "Use why for motivation". `blast-radius/SKILL.md:11` calls itself their companion. `poteto-help/SKILL.md:107` and `docs/guide/03-understand.md:5` group `/how`, `/why`, `/teach` (and `/recall`) as the "understand" set.
- **ketchup uses bro's voice, not unslop.** `ketchup/SKILL.md:11` links `/bro` for voice. It does not name unslop. `ketchup-video` is a variant that follows ketchup.
- **bro and in-your-own-words are one-sentence prompts** (each SKILL.md body is one line, line 7). They are kept as separate slash commands for people. bro's voice is reused by ketchup; in-your-own-words is reused by interrogate.
- **The docs group them by job, not as one writing family.** `docs/guide/03-understand.md`: how, why, teach, recall. `docs/guide/05-build-and-clean.md`: unslop, with `/deslop` and `no-comments`. `docs/guide/09-make-it-yours.md`: technical-writing. `docs/guide/10-recipes-and-pitfalls.md`: in-your-own-words, unslop, bro, ketchup. The README's skill table puts unslop, bro and technical-writing together at the end (README:157-159).
