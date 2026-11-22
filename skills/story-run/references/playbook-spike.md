# Playbook: spike

Read from `aidlc-design` or `aidlc-discover` when an UNKNOWN is a fact a short run can settle (how a library behaves, a query plan, a timing, how a layout feels); the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** A decision's evidence, not code. A spike is a throwaway instrument; the real build follows the plan,
tests first.

**Typical route.** From `aidlc-discover` or `aidlc-design`, before the decision it informs.

**Steps.**
1. Write the question, and the result that would change the choice. When you cannot, there is nothing to spike.
2. Work outside the repository's source, in a scratch folder, and never commit it to the story's branch, as the
   stage's Stop if says.
3. Use only tools already installed. A package you would have to fetch is a new dependency, which a person approves,
   as the stage's Stop if says.
4. Keep to the time-box the person sets; when it runs out, report what is known, as the stage's Stop if says.
5. Build the smallest thing that answers the question: a script for a behaviour or a timing; for a new screen with no
   example in the product, two or three variants behind one switch, each with a screenshot. Comparing two or three
   options side by side before you recommend one is `exhaust-the-design-space`.
6. Observe the thing you are deciding: print the output, log the timing, take the screenshot. The observation is the
   evidence, never an opinion.
7. Write the result in the design note or the evidence pack as a FACT, with the observation and the scratch folder's
   path. A spike's code never moves into the build, as the stage's Stop if says. A choice between screen variants is
   the product owner's, as `aidlc-design` step 2 says for a wireframe.

**Its proof.** The question, the observation, and the UNKNOWN it turned into a FACT; nothing merged.

**Hand back.** The variants or runs, what each showed, your recommendation, and the scratch folder's path; say
plainly that the spike is thrown away.
