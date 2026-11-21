# Brief mode: routes D1 and F0

Sent here from `aidlc-plan` brief mode (route D1) or feature brief mode (route F0), after step 9; this skill's Gate, Stop if and Rules still apply.

**Inputs.** In brief mode, the inputs are the work item (its reproduction and evidence) and the written SOURCE of the
expected behaviour; no spec or design note is needed. For a feature brief, the inputs are the work item and its
acceptance criteria as their owner wrote them; no spec or design note is needed.

Brief mode:
1. Restate the defect: the reproduction, the expected behaviour and where it is written, the actual behaviour. When the
   expected behaviour is written nowhere, stop as this skill's Stop if says.
2. Find the likely area read-only, with the `explorer` agent if the reading is heavy. Label each finding FACT or
   INFERENCE with `file:line`.
3. Ask the three design questions; any yes, stop as this skill's Stop if says.
4. Fill `assets/fix-brief.md` and write it to `plans/<KEY>/fix.md`. Choose USE SKILLS from the practice map
   (`debugging-failures` and `writing-tests` at least). Propose MODE; the engineer chooses it when
   confirming.
5. The engineer confirms the brief by telling you; you write the CONFIRMED line with the name they give, the date
   and how it was confirmed. Check first where you can (ADR 0023): when the engineer approved in the review tool or
   on the tracker, read it there; when the check disagrees, write nothing and say so. Build starts only from a confirmed
   brief. The engineer confirms its TIER with it: that is Ready on route D1, the one decision before Merge (the
   tiers file's decisions table). This skill's Gate holds that decision.
   It covers the brief's ROUTE line too: the engineer checks the route's facts, which
   the tech lead owns (ADR 0027). Mark this stage's row in the index as done.

Feature brief mode (route F0):
1. Restate the outcome and each acceptance criterion as the work item gives it, with its ID, and list every
   ambiguity. State it in the session and go on; the engineer reads it with the brief they confirm. A criterion not
   written on the work item by its owner, or an ambiguity
   only the owner can settle, means stop, as this skill's Stop if says: it is route F1, and `aidlc-start` re-routes it.
2. Find the area read-only, with the `explorer` agent if the reading is heavy. Label each finding FACT or INFERENCE
   with `file:line`.
3. Check the rest of the fast-path test. Any of these means stop, as this skill's Stop if says:
   - the tier rises above 1 (`assets/tiers.md`): what the code shows outranks the first rating;
   - any of the three design questions (`aidlc-design`, step 1) is yes, or uncertain;
   - a new dependency seems necessary;
   - stored data or a schema changes (a migration, a new field, a backfill);
   - the work needs more than one slice, or more than the pull-request size `reviewing-code` gives.
4. Fill `assets/feature-brief.md` and write it to `plans/<KEY>/brief.md`. Map each criterion to a test named with
   its ID. Choose USE SKILLS from the practice map (`writing-tests` at least). Propose MODE; the engineer chooses it when confirming.
5. The engineer confirms the brief by telling you; you write the CONFIRMED line with the name they give, the date
   and how it was confirmed. Check first where you can (ADR 0023): when the engineer approved in the review tool or
   on the tracker, read it there; when the check disagrees, write nothing and say so. Build starts only from a confirmed
   brief. The engineer confirms its TIER with it: that is Ready on route F0, the one decision before Merge (the
   tiers file's decisions table). This skill's Gate holds that decision.
   It covers the brief's ROUTE line too: the engineer checks the route's facts, which
   the tech lead owns (ADR 0027). Mark this stage's row in the index as done, or as stopped with the reason.
