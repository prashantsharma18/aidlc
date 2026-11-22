# Playbook: investigation

Read from `aidlc-discover` when its question is answered by reading, with no code change; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The answer, with its evidence. An investigation is read-only: it changes no code and merges
nothing.

**Typical route.** None: there is no code. Inside a story, `aidlc-discover`.

**Steps.**
1. Trace the code the question is about: its entry points, callers, callees, data, events and configuration. For
   "why is it like this", read the history too: the commits, pull requests and ADRs that shaped it.
2. Label every finding FACT, INFERENCE or UNKNOWN, with its file and line, or the commit or record it comes from.
3. Write the finding: what it is, how it works, where things live, and the gotchas; for a choice between options, a
   recommendation with a table of what each option gets and costs. Write the finding through `unslop`, and answer a "why" from the record, as `why` says.
4. When the question's premise is wrong, say so, with the evidence.
5. When the answer calls for a code change, say so in the finding: inside a story its next stages make it, after this
   stage's Gate; outside one, the person raises a work item at `aidlc-start`.

**Its proof.** The written finding, each claim with its evidence; nothing merged.

**Hand back.** The finding, your own judgement with its reasons, and what stays unknown.
