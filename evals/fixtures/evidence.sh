# Sourced by a case's setup.sh. It writes plans/<KEY>/review-evidence.md from git, section by section, as
# skills/aidlc-build/assets/review-evidence.md asks, so a reviewer agent reads real command output.
# Usage: write_evidence KEY BASE HEAD TESTS_AT_BASE TESTS_AT_HEAD
# Run it from the repository root, on the story branch, with a clean tree. It does not commit.
write_evidence() {
  local key="$1" base="$2" head="$3" before="$4" after="$5"
  {
    printf '# %s · part 1 · review evidence at %s\n\n' "$key" "$(git rev-parse --short "$head")"
    printf '```text\nHEAD       %s\nBASE       %s\nBRANCH     %s\nWRITTEN    2026-11-20, by the review session\n' \
      "$head" "$base" "$(git branch --show-current)"
    git log --format='COMMITS    %h %s' "$base..$head"
    printf '```\n\n'
    printf '## Changed files (reviewer-compliance)\n'
    printf '`git diff --stat --no-renames <base> HEAD`, then `git diff --name-only --no-renames <base> HEAD`.\n\n```text\n'
    git diff --stat --no-renames "$base" "$head"
    git diff --name-only --no-renames "$base" "$head"
    printf '```\n\n## Test files (reviewer-tests, reviewer-compliance)\n'
    printf "\`git diff --no-renames <base> HEAD -- ':(top)tests/'\`\n\n\`\`\`text\n"
    git diff --no-renames "$base" "$head" -- ':(top)tests/'
    printf '```\n\n## Test count (reviewer-tests)\n'
    printf '`python3 -m unittest discover -s tests -t .` at BASE and at HEAD.\n\n```text\n'
    printf 'BASE       %s passed, 0 failed, 0 skipped\nHEAD       %s passed, 0 failed, 0 skipped\n```\n\n' "$before" "$after"
    printf '## Commands run at HEAD (reviewer-tests)\n\n```text\npython3 -m unittest discover -s tests -t .    exit 0\n```\n\n'
    printf '## Dependency manifests (reviewer-compliance)\nThe repository has no manifest (standard library only).\n\n'
    printf '```text\nno change\n```\n\n'
    printf '## Check configuration (reviewer-compliance)\n\n```text\nno change\n```\n\n'
    printf '## Story documents (reviewer-compliance)\n'
    printf "\`git diff <base> HEAD -- ':(top)plans/%s/' ':(top,exclude)plans/%s/review-evidence.md'\`\n\n" "$key" "$key"
    # A progress note holds three backticks, so this output is fenced with four.
    printf '````text\n'
    git diff "$base" "$head" -- ":(top)plans/$key/" ":(top,exclude)plans/$key/review-evidence.md"
    printf '````\n\n## Added suppressions, skips and exceptions (reviewer-compliance)\n\n```text\n'
    git diff -U0 --no-renames "$base" "$head" -- ':(top)' ":(top,exclude)plans/$key/" \
      | grep -E '^\+[^+].*(noqa|type: ignore|pylint: disable|unittest\.skip|pytest\.mark\.skip|xfail|aidlc-exception)' \
      || echo none
    printf '```\n\n## Recipe commits (reviewer-compliance)\n\n```text\nnone\n```\n'
  } > "plans/$key/review-evidence.md"
}
