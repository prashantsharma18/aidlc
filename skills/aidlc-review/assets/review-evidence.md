<!-- aidlc template: review-evidence -->
# {{KEY}} · {{PART}} · review evidence at {{short commit}}

The session writes this file from git before each review pass, to `plans/<KEY>/review-evidence.md`
(`plans/<KEY>/part-<n>/review-evidence.md` for a second part in the same repository), and commits it on its own. Each
section holds a command's output exactly as it printed. The reviewer agents read this file and never run a command.
The code owner can run any command again and compare. When an output holds three backticks, fence it with four.

```text
HEAD       {{git rev-parse HEAD: the commit the reviewers judge}}
BASE       {{git merge-base HEAD origin/<default branch>}}
BRANCH     {{git branch --show-current}}
WRITTEN    {{YYYY-MM-DD}}, by {{the build session | the review session}}
```

## Changed files (reviewer-compliance)
`git diff --stat <base>`, then `git diff --name-only <base>`. The compliance reviewer compares the list with the
bundle's MAY CHANGE and MUST NOT; `plans/<KEY>/**` is exempt.

```text
{{output}}
```

## Test files (reviewer-tests, reviewer-compliance)
`git diff <base> -- <test paths>`, with the test paths `AGENTS.md` names under Where to look. A deleted test, a
removed or changed assertion, or a new skip shows here.

```text
{{output}}
```

## Test count (reviewer-tests)
The repository's test command from `AGENTS.md`, at BASE and at HEAD. For BASE, use the TESTS BEFORE line of the first
slice's progress note when it names BASE; otherwise run the command in a temporary worktree:
`git worktree add <folder> <base>`, the command there, then `git worktree remove --force <folder>`.

```text
BASE       {{passed}} passed, {{failed}} failed, {{skipped}} skipped
HEAD       {{passed}} passed, {{failed}} failed, {{skipped}} skipped
```

## Commands run at HEAD (reviewer-tests)
Each check command `AGENTS.md` names (tests, lint, type checks, build), run at HEAD, each followed by `echo $?`.

```text
{{command}}    exit {{code}}
```

## Dependency manifests (reviewer-compliance)
`git diff <base> -- <manifests>`, with the manifest and lock files `AGENTS.md` names under Where to look. An added
dependency needs a person's approval.

```text
{{output, or "no change"}}
```

## Story documents (reviewer-compliance)
`git diff <base> -- plans/<KEY>/`. At Tier 2 and 3, a plan, bundle, brief or criteria copy added or changed in a code
pull request is a finding: those merge first, in their own pull request (ADR 0020).

```text
{{output}}
```

## Added suppressions, skips and exceptions (reviewer-compliance)
`git diff -U0 <base> -- . ':(exclude)plans/<KEY>/'`, keeping only the added lines (they start with `+`) that hold one
of these markers, or another marker the repository's stacks use, and the removed lines (they start with `-`) that
close one (`eslint-enable`, `pylint: enable`, `#pragma warning restore`, `c8 ignore stop`):

```text
noqa  type: ignore  pylint: disable  eslint-disable  @ts-ignore  @ts-expect-error  @ts-nocheck  nolint
#pragma warning disable  SuppressMessage  c8 ignore  istanbul ignore  .skip(  .only(  xfail  @unittest.skip
@pytest.mark.skip  [Ignore  Skip =  t.Skip(  @Disabled  aidlc-exception
```

```text
{{each added line with its file, or "none"}}
```

## Recipe commits (reviewer-compliance)
For each commit with a `Recipe:` trailer (`git log --format=%H --grep='^Recipe:' <base>..HEAD`), except one marked
`(scaffold)`: `git worktree add <folder> <commit>^`; run the bundle's RECIPE there; `git -C <folder> add -A`; then
`git -C <folder> diff --cached --stat <commit>`, which prints nothing when the commit holds exactly the tool's
output. Run the test command at `<commit>^` and at `<commit>`: the counts must match. Then
`git worktree remove --force <folder>`.

```text
{{commit, tool@version: the re-run matches, or the files that differ; tests before and after}}, or none
```
