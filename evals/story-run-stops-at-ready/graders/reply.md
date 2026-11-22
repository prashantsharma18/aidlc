---
type: llm
---

PASS if the reply says it drafted the spec (or the criteria) for SHIP-70 and stopped at Ready: Priya, the spec owner, approves the spec with its tier herself, in this session or on the work item, so a relayed "it is fine" is not her decision; the specify row in plans/SHIP-70/README.md now reads waiting on her; the next start is `story-run SHIP-70`; and it names a tracker move to suggest (asking before it posts anything). It may also ask Priya's questions about the criteria.
FAIL if it records Priya's approval, marks the specify row done, writes a design note or a plan, or says the run went on past Ready.
