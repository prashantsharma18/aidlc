# A local container for the behaviour evals

This is aidlc's own maintainer tooling. It is not shipped to teams, and no team needs it.

The cases that need Bash cannot run where Claude Code's Bash sandbox refuses. On this project's WSL machine it
refuses because `~/.docker/contexts` is a symbolic link. The `evals` workflow solves this with a clean runner. This
image gives you the same tools on your own machine: git, Python 3, bubblewrap and socat for the sandbox, Node 22, and
Claude Code at the version the workflow pins.

These notes sit next to the Dockerfile, not in `evals/README.md`, because the two change together. `evals/README.md`
stays about the cases and points here.

## Build

From the repository root:

```bash
docker build -t aidlc-evals:2.1.296 evals/container
```

The tag names the Claude Code version. When `.github/workflows/evals.yml` moves to a new version, change the
Dockerfile to match and build a new tag. `scripts/test_evals.py` fails until the two match.

## Credentials

Pass one credential at run time, by name only. Docker then copies its value from your shell into the container.
It never lands in a file, an image layer or your shell history.

- An API key: `read -rs ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY`, then `-e ANTHROPIC_API_KEY`.
- A subscription: run `claude setup-token` on your machine. Then `read -rs CLAUDE_CODE_OAUTH_TOKEN && export
  CLAUDE_CODE_OAUTH_TOKEN`, and pass `-e CLAUDE_CODE_OAUTH_TOKEN` instead.

Never mount `~/.claude`, `~/.docker` or any other credential file into the container. Never write a credential into a
file in the repository, which is mounted read-write.

## Run

From the repository root:

```bash
docker run --rm -it --security-opt seccomp=unconfined -e ANTHROPIC_API_KEY -v "$PWD":/work aidlc-evals:2.1.296 bash
```

With a subscription token, the same command with the other name:

```bash
docker run --rm -it --security-opt seccomp=unconfined -e CLAUDE_CODE_OAUTH_TOKEN -v "$PWD":/work aidlc-evals:2.1.296 bash
```

Inside the container, you are the unprivileged user `node` in `/work`. Check the sandbox first, then run the smoke
from `evals/README.md`. The smoke spends money: up to the `--max-cost-usd` it names.

```bash
bwrap --ro-bind / / --dev /dev --proc /proc true && echo "sandbox ok"
claude plugin eval . --trust-plugin --scaffold --allow-tools Write Edit "Bash(python3 *)" "Bash(git *)" \
  --no-publish --runs 1 --ablation none --max-cost-usd 10
```

Results go to `evals/results/` on your machine, because `/work` is the mounted repository. `--rm` throws the
container away when you leave it, with any Claude Code state it made.

## Why `--security-opt seccomp=unconfined`

Claude Code's Bash sandbox runs each command under bubblewrap, which needs a new user namespace. Docker's default
system-call filter (seccomp) blocks that. The risk in one sentence: with the filter off, a process in the container
can make every system call the kernel offers, so a kernel bug is easier to reach from inside; keep this container
throwaway, with only the repository mounted.

This was the smallest set that worked, tried on 2026-11-21 on Docker Desktop 4.72.0 (engine 29.4.2) under WSL 2,
with `bwrap --ro-bind / / --dev /dev --proc /proc true`:

| Flags | Result |
|---|---|
| none | fails: no permission to create a namespace |
| `--security-opt apparmor=unconfined` | fails, the same way |
| `--cap-add SYS_ADMIN` | fails: `pivot_root` not permitted |
| `--security-opt seccomp=unconfined` | works, also with `--unshare-all` |

Docker Desktop's virtual machine has no AppArmor. On a Linux host that runs AppArmor (Ubuntu, for example), the
container's AppArmor profile may block bubblewrap too. If the check above fails there, add
`--security-opt apparmor=unconfined`; this was not tried here. Never use `--privileged`: it gives the container
the whole host.

## Notes

- The image runs as `node`, uid 1000. Files the run writes in `/work` belong to uid 1000. That is your own user on
  most Linux and WSL machines, so git inside sees a repository you own.
- The image sets `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`, as the workflow does, so the commands the session runs do not
  see the credential.
- The base image is pinned by tag and digest. To move it, pull the new tag, read its digest
  (`docker buildx imagetools inspect node:<tag>`), and change both in the Dockerfile.
