<!-- aidlc template: review-evidence -->
# {{KEY}} · {{PART}} · review evidence at {{short commit}}

The session writes this file from git before each review pass, to `plans/<KEY>/review-evidence.md`
(`plans/<KEY>/part-<n>/review-evidence.md` for a second part in the same repository), and commits it on its own. Each
section holds a command's output exactly as it printed. The reviewer agents read this file and never run a command.
The code owner can run any command again and compare. When an output holds three backticks, fence it with four.

Four rules keep the evidence from being empty by accident. Write the file only from a clean tree
(`git status --porcelain` prints nothing). Every diff below compares `<base>` with HEAD, never the working tree.
Run every command from the repository root (`cd "$(git rev-parse --show-toplevel)"`), and start every path pattern
with `:(top)`: from a subfolder, a pattern without it matches only files under that folder. Quote every pathspec
pattern, for example `':(top)*_test.go'`: the shell expands an unquoted pattern to files that did not change, and the
diff then prints nothing.

```text
HEAD       {{git rev-parse HEAD: the commit the reviewers judge}}
BASE       {{git fetch, then git merge-base HEAD origin/<default branch>}}
BRANCH     {{git branch --show-current}}
WRITTEN    {{YYYY-MM-DD}}, by {{the build session | the review session}}
STANDARD   {{on route S: the class, and each limit with how it held | none}}
```

## Changed files (reviewer-compliance)
`git diff --stat --no-renames <base> HEAD`, then `git diff --name-only --no-renames <base> HEAD`. The compliance reviewer compares the list with the
bundle's MAY CHANGE and MUST NOT; `plans/<KEY>/**` is exempt.

```text
{{output}}
```

## Test files (reviewer-tests, reviewer-compliance)
`git diff --no-renames <base> HEAD -- ':(top)<test path>'`, with one quoted `:(top)` pattern for each test path
`AGENTS.md` names under Where to look (for example `':(top)tests/' ':(top)*_test.go'`). A deleted test, a removed or
changed assertion, or a new skip shows here.

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
`git diff <base> HEAD -- ':(top)<manifest>'`, with one quoted `:(top)` pattern for each manifest and lock file
`AGENTS.md` names under Where to look. An added dependency needs a person's approval.

```text
{{output, or "no change"}}
```

## Check configuration (reviewer-compliance)
`git diff <base> HEAD -- ':(top)<check configuration path>'`, with one quoted `:(top)` pattern for each lint, type,
test, coverage and CI configuration path `AGENTS.md` names under Where to look. A loosened rule, a lowered threshold
or a removed step is a finding.

```text
{{output, or "no change"}}
```

## Story documents (reviewer-compliance)
`git diff <base> HEAD -- ':(top)plans/<KEY>/' ':(top,exclude)plans/<KEY>/review-evidence.md'`, which leaves out this
file (for a second part, exclude `':(top,exclude)plans/<KEY>/part-<n>/review-evidence.md'` instead). At Tier 2 and 3,
a plan, bundle, brief or criteria copy added or changed in a code pull request is a finding: those merge first, in
their own pull request (ADR 0020).

```text
{{output}}
```

## Added suppressions, skips and exceptions (reviewer-compliance)
`git diff -U0 --no-renames <base> HEAD -- ':(top)' ':(top,exclude)plans/<KEY>/'`, keeping only the added lines (they start with `+`) that hold one
of these markers, or another marker the repository's stacks use, and the removed lines (they start with `-`) that
close one (`eslint-enable`, `pylint: enable`, `#pragma warning restore`, `c8 ignore stop`):

```text
noqa  type: ignore  pylint: disable  eslint-disable  @ts-ignore  @ts-expect-error  @ts-nocheck  nolint
#pragma warning disable  SuppressMessage  c8 ignore  istanbul ignore  .skip(  .only(  xfail  @unittest.skip
@pytest.mark.skip  [Ignore  Skip =  t.Skip(  @Disabled  aidlc-exception
xit(  xdescribe(  @Ignore  @SuppressWarnings  #[ignore]  <NoWarn>
```

```text
{{each added line with its file, or "none"}}
```

## Recipe commits (reviewer-compliance)
For each commit with a `Recipe:` trailer (`git log --format=%H --grep='^Recipe:' <base>..HEAD`), except one marked
`(scaffold)`: `git worktree add <folder> <commit>^`. Then, in that order:

1. Run the test command there first, for the parent's count, because the recipe then changes the worktree.
   Then `git -C <folder> clean -fd`, so the test run leaves no stray file.
2. Run the bundle's RECIPE there, then `git -C <folder> add -A`.
3. `git -C <folder> diff --cached --stat <commit>` prints nothing when the commit holds exactly the tool's output.
4. Run the test command there again, for the commit's count: when step 3 printed nothing, the worktree now holds
   the commit's files. The two counts must match.
5. Add the changed assertion lines: `git diff <commit>^ <commit> -- ':(top)<test path>'` (quote each pattern). Then
   `git worktree remove --force <folder>`.

```text
{{commit, tool@version: the re-run matches, or the files that differ; tests before and after; the changed assertion lines}}, or none
```
