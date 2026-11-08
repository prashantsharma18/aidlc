---
tags: [route]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

/aidlc:aidlc-start SHIP-40. The work item, written by its product owner: 'Shipping labels start with "SHIP-". AC-1: label("ab12") returns "SHIP-AB12". AC-2: an empty code raises ValueError.'
