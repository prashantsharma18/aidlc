# Upgrade tools: which may be a recipe

A recipe commit needs a deterministic tool: the same code in, the same diff out, re-run by a check (core's recipe
rule, ADR 0012). For .NET:

| Tool | Deterministic? | How to use it here |
|---|---|---|
| `retarget.py` (this factory, `scripts/retarget.py`) | yes | the recipe: changes the target framework of SDK-style projects and drops the reference-assemblies package |
| GitHub Copilot modernization agent (in Visual Studio; it replaces the .NET Upgrade Assistant, which Microsoft deprecated) | no: an AI agent | allowed as an assistant, but its changes are ordinary code under every gate, never a recipe commit |
| .NET Upgrade Assistant | deprecated | not used for new work |
| OpenRewrite C# recipes (through Moderne, under a proprietary licence) | yes | only after the organisation decides on the licence; then approved per plan with its version |
| Roslyn analyzers and their code fixes, applied by a command | yes, for a pinned analyzer version | a recipe when run as one approved command |

Whatever the tool, the plan names it and its version, and the person approves it as a dependency.
