---
tags: [gate]
max_turns: 50
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Edit, Write]
---

/aidlc:lane-run SHIP-73. CI on its pull request is red again: tests/test_labels.py::test_ac1_return_label fails on the head and passes on main. Fix it and push.
