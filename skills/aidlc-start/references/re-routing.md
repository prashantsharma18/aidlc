# Re-routing: an index for this key already exists

Sent here from `aidlc-start` step 7, when the story's index already exists; this skill's Gate, Stop if and Rules still apply.

- keep every row marked done; give the new route's other stages a row "to do"; a row marked stopped becomes "to
  do" when the new route has that stage, and is removed otherwise;
- write the ROUTE line as `<new route>   (re-routed from <old route>, <YYYY-MM-DD>: <reason>)`;
- keep the old brief (`fix.md` or `brief.md`) as history: the new route's documents replace it;
- when the new route spans several repositories, run this at the workspace root: it writes
  `stories/<KEY>/README.md` there with the story-level rows, and the repository's `plans/<KEY>/README.md` becomes
  that repository's part index when `aidlc-plan` runs for the part;
