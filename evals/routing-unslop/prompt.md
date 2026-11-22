---
tags: [routing]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

Unslop this before I post it to the team.
Reply with the cleaned text only.

We delved into the ETA outage — a crucial, pivotal moment for the team. In order to fix it, the on-call engineer
rolled back the deploy with the command below, ensuring stability. It is important to note that the cap lives in
`src/shipments/eta.py`. I hope this helps!

```bash
kubectl rollout undo deployment/eta-api --namespace shipments
```
