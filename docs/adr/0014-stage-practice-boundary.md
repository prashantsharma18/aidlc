# 0014 · Stages load practices; one map

Status: Accepted (2026-11-06). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-06-stage-practice-boundary.md`

## Context
Practices loaded only when Claude chose them by description, which varies from run to run. Stage skills mentioned
practices in passing, some repeated a practice's technique, and some practices contradicted the gates. No single page
showed the flow.

## Decision
- A stage says when, what must hold and who approves; a practice says how. A stage step that needs a technique says
  "Load the `<practice>` skill" and keeps its gate in one sentence. `scripts/test_loads.py` holds the table.
- A commanded load that fails is a stop. The plan chooses each slice's practices from the map into USE SKILLS; the
  tech lead approves them; the build loads them or stops.
- `reviewing-code` is loadable. One severity scheme: high, medium, low, plus question; high and medium block the merge
  until fixed or dismissed with a reason.
- `using-aidlc` is the single map: the lifecycle and the practice map. No session hook.
- `writing-documentation` joins the practices.
- Practices defer to gates and to stage templates; one number per measure.

## Consequences
- About 300 more tokens of descriptions per session.
- Changing which practice a stage loads means changing the stage text and the test table together.
