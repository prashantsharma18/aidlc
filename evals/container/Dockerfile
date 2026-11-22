# aidlc maintainer tooling, not shipped to teams: a local container for the behaviour evals, so the cases that need
# Bash run where the Bash sandbox works. How to build and run it: evals/container/README.md.
FROM node:22.23.5-trixie-slim@sha256:68c76cfad89921b927eae28ba21407475e29d0ce450afcdbe70c1532db042b64

# git and python3 for the scaffolds and the fixture's tests; bubblewrap and socat for Claude Code's Bash sandbox.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates git python3 bubblewrap socat \
 && rm -rf /var/lib/apt/lists/*

# Pinned to the version .github/workflows/evals.yml installs; scripts/test_evals.py checks that the two match.
RUN npm install -g @anthropic-ai/claude-code@2.1.296 && npm cache clean --force

# The base image's unprivileged user (uid 1000). The repository is mounted at /work.
USER node
# safe.directory: git inside still works when the mounted repository belongs to a uid other than 1000.
RUN git config --global user.name eval && git config --global user.email eval@example.com \
 && git config --global --add safe.directory /work
# Keep the credential out of the environment of the commands the session runs, as the evals workflow does.
ENV CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1
WORKDIR /work
