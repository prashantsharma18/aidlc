# Amendment mode

Sent here from `aidlc-specify` amendment mode, before its last step; this skill's Gate, Stop if and Rules still apply.

1. Raise it against the criterion ID: quote the criterion and say exactly what conflicts.
2. Classify it: a misreading (the spec is right; fix the reading) or a gap or conflict (someone must decide). If unsure, treat it as a gap.
3. For a gap, prepare the decision for the criterion's owner, with the options and their consequences. Never pick one. Until the owner decides, stop as this skill's Stop if says.
4. Only after the owner has decided, and only from that decision: write the new version of the spec, with its version raised (v1 to v2) and an Amendments line with the date, criterion, reason and decider. The person saves it.
5. List everything that cites the criterion (tests, plan, task bundles, evidence) and say that the plan returns for
   approval, because the criteria changed. Then the tech lead classifies each part by its state:

   | Part's state | Action |
   |---|---|
   | Not started | Plans against the new version |
   | Building or in review | Re-plans on the same branch; the same pull request continues |
   | Merged, flag off | A revision pull request in that repository (see `aidlc-plan`), or a revert if its code owner chooses |
   | Unaffected | The tech lead decides and tells you why; you record it as an `UNAFFECTED <repository> spec v<n>: <why>, <who>, <date>` line in the story index, with how it was confirmed |
   | Released | Not a change request: a new story with its own key |

   The classification is the tech lead's decision, as this skill's Gate says.

   For a story across several repositories, raise the CURRENT line in the story index. Then check the parts yourself:
   for each part, run `git -C <repository> fetch`, then read the part's PINS line on its default branch, with
   `git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`, and mark every part pinned to the old spec
   "re-plan" in `status.md`. In the original story's index, add an `aidlc-specify (amendment)` row that
   links the change request.
