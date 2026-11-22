# Amendment mode: a contract change

Sent here from `aidlc-design` amendment mode, before its last step; this skill's Gate, Stop if and Rules still apply.

1. Quote the contract and the finding, and list the parts that consume it from the coordination plan.
2. Draft the contract's next version and the updated consumer tests. Say whether the change is additive (minor) or
   breaking (major, done by expand and contract). The provider's contract check (oasdiff against the last
   published tag) must agree with that classification.
3. The consumers approve the new version on the tracker. Record it in the ADR and in the story index's CURRENT line.
   Once the provider's pull request merges, its default branch publishes the tag `api-v<version>`. Each consumer
   moves its copy to that tag, with the commands in `designing-apis`, in a slice whose MAY CHANGE names
   `contracts/<provider>/**`. Never point a consumer at an unpublished version. The consumers' approval is this
   skill's Gate's decision.
4. For each part, run `git -C <repository> fetch`, then read each part's PINS line on its default branch, with
   `git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`, and mark every part pinned to the old
   version "re-plan" in `status.md`. Those parts return to `aidlc-plan`; their bundles are approved again. In one
   repository there is no coordination plan: list the bundles that pin the old version and mark them for re-plan.
