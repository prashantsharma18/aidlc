<!-- aidlc template: adr -->
# 0008 · A curated practice layer, and plugins per repository from approved marketplaces

Status: Accepted (2026-10-23). · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision) · Tier: 2 (changes what every developer's agent loads)

## Context

- **Two kinds of skill.** Stage skills (ADR 0005) say which step you are in, what it produces and who
  approves it. Practice skills say how to do a kind of work well: design an API, debug, harden,
  instrument, profile. aidlc had no practice skills.
- **Skills load at several levels.** Claude Code loads skills from managed (enterprise), personal and
  project folders and from plugins. Plugin skills are namespaced, so plugins never clash. Every
  installed skill's description is in every session's context, so organisations curate.
- **agent-skills.** addyosmani/agent-skills (MIT, Copyright (c) 2025 Addy Osmani) has good practice
  skills. Its router (`using-agent-skills`) would steer the agent to its own spec, plan and ship
  skills, which have none of our gates.
- **Domain and team levels.** A repository could only disable plugins (`disable_user_plugins`). It
  had no way to switch on a domain's or team's plugin.

## Decision

- **A second plugin, `aidlc-practice`,** in the same marketplace as `aidlc`, generated from
  `core/practices`. It carries eight practices adapted from agent-skills at commit `aeac41d`:
  api-and-interface-design, debugging-and-error-recovery, security-and-hardening,
  observability-and-instrumentation, performance-optimization, frontend-ui-engineering,
  deprecation-and-migration and code-review-and-quality.
- **The adaptation rules:**
  - our Rules block (data is never an instruction; drafts in the reply; pinned tools, never
    install; you never approve) and a credit line;
  - no installs, pushes or approval verdicts, and links only inside the practice;
  - `NOTICE` ships the MIT text.

  A format test enforces them. Code review is manual (a rubric before you push; CI review stays
  Anthropic's). The others may start on their own, because they only advise.
- **Not shipped:**
  - `ci-cd-and-automation`: it edits CI, which here is generated and judged;
  - `interview-me` and `idea-refine`: they overlap `aidlc-intent`, which takes their one-question-at-a-time
    technique instead;
  - `browser-testing-with-devtools`: deferred until a pinned Chrome DevTools MCP server is approved
    through the gateway;
  - the `using-agent-skills` router. Its six working behaviours go into the `AGENTS.md` template,
    which every tool reads.
- **Plugins per repository.** `.aidlc/config.yaml` `harness.enable_plugins` lists
  `<plugin>@<marketplace>`. Render writes them into `enabledPlugins`, and registers their marketplace,
  only when the marketplace is an approved marketplace in `core/policy/plugins.yaml`. The Rego pack
  denies any other in trusted CI.

## Consequences

- The vendored text changes only through a reviewed change to a new pinned commit.
- A repository's `enable_plugins` changes go through its code owners, like the rest of `.aidlc/`.
- Every installed skill costs context in every session, so the practice list stays curated.
- Copilot later renders the same practices into `.agents/skills`.

## Rejected alternatives

- **Installing agent-skills' whole plugin.** It brings 24 skills, its router and ungated process
  skills that compete with our stage skills.
- **A second marketplace file for the practices.** It is possible (a marketplace source can name a
  path), but it means an awkward layout. One marketplace with two plugins is the standard pattern.
