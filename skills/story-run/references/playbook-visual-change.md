# Playbook: visual change

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `visual-change`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** How a screen looks. The baseline is the check, and you never touch it.

**Typical route.** F0 or F1 for a change to how a page looks; S for an upgrade (a framework or a design system) that
must not change it.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `building-user-interfaces`, `testing-in-browser`.

**Steps.**
1. Record the baseline first, before any change: a screenshot of each screen the slice touches, in each of its states
   (empty, loading, error, full), with the repository's visual comparison tool. Without a baseline, there is no claim
   that a page looks the same.
2. A baseline image, and the harness that compares it, are an assertion, as `aidlc-build`'s Stop if says: never
   update one to make a difference pass, and never change the harness. Never restructure a component to hide a
   difference either: that passes a check by lowering the bar, as `aidlc-build`'s Stop if says. A baseline that looks
   wrong is its owner's to decide.
3. Change one component at a time; shared parts first.
4. Compare by image difference, not by eye. A difference fails until someone explains it. For a change meant to show,
   the new screenshot is reviewed with the change, against the design note's UI REFERENCE.
5. With no comparison tool in the repository, proposing one is a new dependency, which a person approves, as
   `aidlc-build`'s Stop if says.

**Its proof.** The baseline screenshots, the screenshots after, and the image difference for each, zero or explained;
for a change meant to show, the reference it matches.

**Hand back.** The screens changed, the difference for each, and where the baseline is kept.
