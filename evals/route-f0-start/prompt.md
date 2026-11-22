---
tags: [route]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

/aidlc:aidlc-start SHIP-40. The work item, written by its product owner: 'Return labels: add return_label(code) next to label(). AC-1: return_label("ab12") returns "RETURN-AB12". AC-2: an empty code raises ValueError. label() does not change.'
