# Plan 6: the shipment-tracking demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the aidlc framework on story SHIP-1, which crosses two small containerised repositories in the `~/work/shipment-tracking` workspace, with only the aidlc harness loaded.

**Architecture:** The framework gains one command, `aidlc workspace init`, which writes `WORKSPACE.md`, a `CLAUDE.md` that imports it, and a read-only Claude Code harness for the workspace root. Two baseline repositories (a .NET 10 API and a React portal), the workspace repository and Docker Compose are built directly, as the "existing product". The story itself runs only through headless Claude Code sessions started in each repository, with the plugins loaded from this checkout. The user approves at every gate.

**Tech Stack:** Python 3.12 (framework; stdlib, PyYAML, jsonschema). .NET 10 SDK 10.0.113, ASP.NET Core minimal API, xUnit, YamlDotNet. Node 22 (nvm), React, TypeScript, Vite, Vitest, Testing Library. Docker Compose, nginx-unprivileged. Claude Code headless (`claude -p`).

**Spec:** `docs/design/2026-10-23-plan-06-demo-design.md` (approved by the user 2026-10-23).

## Global Constraints

- Workspace: `~/work/shipment-tracking`. Repositories: `shipments-api` (owner "Logistics team", profile `dotnet`) and `customer-portal` (owner "Web team", profile `node`).
- Local git only. No GitHub repositories, no push, no CI for the demo.
- Story: SHIP-1, "Show customers an estimated delivery window". Branch in each repository: `feat/SHIP-1-delivery-window`. Flags: `eta-in-api` (API), `show-delivery-window` (portal), both off by default.
- Ports: portal `8080`, API `8081` on localhost.
- Isolation: no plugin other than `aidlc` and `aidlc-practice` may load in the workspace or the repositories. User plugins to disable: `superpowers@claude-plugins-official`, `skill-creator@claude-plugins-official`, `platform@ai-assets`, `baseline@local`, `discovery-pack@local`, `spec-pack@local`, `impl-pack@local`, `governance-pack@local`.
- Every story session: `claude -p … --setting-sources project,local --plugin-dir ~/demos/aidlc/plugins/aidlc --plugin-dir ~/demos/aidlc/plugins/aidlc-practice --permission-mode dontAsk --model sonnet`, with `AIDLC_UNATTENDED=1`, started in a trusted folder.
- Agents never run Docker. The driver builds and runs containers.
- Commits: `prashantsharma18 <6386481+prashantsharma18@users.noreply.github.com>`, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. The driver's saves of approved drafts say "saved by the driver after the user's approval".
- Framework: never change an existing test assertion to make a test pass; `make test` gates every framework commit.

## Review Focus

1. `aidlc workspace init` run twice, or over a hand-written `WORKSPACE.md` → every existing file is skipped, never overwritten (Task 1 test `test_never_overwrites`).
2. `--repo` naming a folder that is not a git repository root, or a path that leaves the workspace (`../x`) → exit 2 with a message, nothing written (Task 1 tests `test_rejects_non_repo`, `test_rejects_escaping_repo`).
3. The portal's flag script with no `FLAG_` variables, or a junk value → valid JSON, every flag `false` (Task 3 step "flag script").
4. The portal when `/config.json` is missing or malformed → flags off, the page still works (Task 3 test `missing config means every flag is off`).
5. The API given an unknown, oddly cased or URL-encoded id → 404 or the match, never a 500 (Task 2 tests `Unknown_shipment_is_404`, `Lookup_ignores_case`, `Encoded_id_is_404`).

---

### Task 1: `aidlc workspace init` (framework)

**Files:**
- Create: `cli/aidlc/workspace.py`
- Create: `cli/aidlc/commands/workspace_cmd.py`
- Modify: `cli/aidlc/commands/__init__.py` (register the module)
- Create: `docs/harness/workspace.md`
- Test: `tests/unit/test_workspace.py`

**Interfaces:**
- Consumes: `aidlc.repo._write(root, rel, text, report)`, `aidlc.templates.load_template`, `aidlc.templates.render`, `aidlc.policy.load_policy("permissions")["secret_paths"]`, `aidlc.adapters.claude_code.SCHEMA`, `aidlc.adapters.claude_code._sandbox_paths`, `aidlc.adapters.claude_code.PLUGIN_ID`.
- Produces: `init_workspace(root: Path, key: str, title: str, repos: list[tuple[str, str]], disable_plugins: list[str]) -> list[tuple[str, str]]` and the CLI `aidlc workspace init <dir> --key K --title T --repo NAME=OWNER… [--disable-plugin ID…]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_workspace.py
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from aidlc.workspace import init_workspace
from tests.helpers import run_cli

PLUGINS = ["superpowers@claude-plugins-official", "baseline@local"]


def _workspace(tmp: str) -> Path:
    root = Path(tmp)
    for name in ("shipments-api", "customer-portal"):
        subprocess.run(["git", "init", "-q", str(root / name)], check=True)
    return root


class WorkspaceInitTest(unittest.TestCase):
    def test_writes_the_guide_the_import_and_a_read_only_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            report = dict(init_workspace(root, "SHIP-1", "Delivery window",
                                         [("shipments-api", "Logistics team"), ("customer-portal", "Web team")],
                                         PLUGINS))
            self.assertEqual(report, {"WORKSPACE.md": "created", "CLAUDE.md": "created",
                                      ".claude/settings.json": "created"})
            guide = (root / "WORKSPACE.md").read_text(encoding="utf-8")
            self.assertIn("SHIP-1 (Delivery window)", guide)
            self.assertIn("| shipments-api | Logistics team |", guide)
            self.assertIn("| customer-portal | Web team |", guide)
            self.assertNotIn("| <repo> |", guide)
            self.assertIn("@WORKSPACE.md", (root / "CLAUDE.md").read_text(encoding="utf-8"))
            s = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
            for denied in ("Edit", "Write", "NotebookEdit", "Bash(git commit*)", "Bash(git push*)"):
                self.assertIn(denied, s["permissions"]["deny"])
            self.assertIn("Read(.env)", s["permissions"]["deny"])   # the policy's secret_paths, as render writes them
            self.assertEqual(s["permissions"]["disableBypassPermissionsMode"], "disable")
            self.assertEqual(s["sandbox"]["filesystem"]["denyWrite"], ["./"])
            self.assertFalse(s["sandbox"]["autoAllowBashIfSandboxed"])
            self.assertEqual(s["enabledPlugins"], {p: False for p in PLUGINS})
            self.assertFalse(s["autoMemoryEnabled"])

    def test_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            (root / "WORKSPACE.md").write_text("# hand written\n", encoding="utf-8")
            report = dict(init_workspace(root, "SHIP-1", "t", [("shipments-api", "o")], []))
            self.assertEqual(report["WORKSPACE.md"], "skipped (exists)")
            self.assertEqual((root / "WORKSPACE.md").read_text(encoding="utf-8"), "# hand written\n")
            again = dict(init_workspace(root, "SHIP-1", "t", [("shipments-api", "o")], []))
            self.assertTrue(all(v == "skipped (exists)" for v in again.values()))

    def test_rejects_non_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            (root / "notes").mkdir()
            with self.assertRaisesRegex(ValueError, "not the root of a git repository"):
                init_workspace(root, "SHIP-1", "t", [("notes", "o")], [])
            self.assertFalse((root / "WORKSPACE.md").exists())

    def test_rejects_escaping_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            with self.assertRaisesRegex(ValueError, "a folder directly inside the workspace"):
                init_workspace(root, "SHIP-1", "t", [("../shipments-api", "o")], [])

    def test_rejects_a_bad_plugin_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            with self.assertRaisesRegex(ValueError, "<plugin>@<marketplace>"):
                init_workspace(root, "SHIP-1", "t", [("shipments-api", "o")], ["superpowers"])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            code, out, _ = run_cli("workspace", "init", str(root), "--key", "SHIP-1", "--title", "t",
                                   "--repo", "shipments-api=Logistics team",
                                   "--disable-plugin", "superpowers@claude-plugins-official")
            self.assertEqual(code, 0)
            self.assertIn("created", out)
            code, _, err = run_cli("workspace", "init", str(root), "--key", "SHIP-1", "--title", "t",
                                   "--repo", "no-equals-sign")
            self.assertEqual(code, 2)
            self.assertIn("NAME=OWNER", err)
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_workspace -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'aidlc.workspace'`.

- [ ] **Step 3: Implement**

```python
# cli/aidlc/workspace.py
"""A workspace root: WORKSPACE.md, a CLAUDE.md that imports it, and a read-only harness (Plan 6).
A session started here reads every repository and writes none; work happens in a session started
inside one repository."""
from __future__ import annotations

import json
from pathlib import Path

from .adapters.claude_code import PLUGIN_ID, SCHEMA, _sandbox_paths
from .policy import load_policy
from .repo import _write
from .templates import load_template, render

READ_ONLY_SHELL = ["git status", "git log*", "git show*", "git diff*", "ls*"]
DENY_TOOLS = ["Edit", "Write", "NotebookEdit", "Bash(git commit*)", "Bash(git push*)",
              "Bash(git checkout*)", "Bash(git switch*)", "Bash(git reset*)"]
ROW_PLACEHOLDER = "| <repo> | <team> | <slice, role> | AGENTS.md |"


def _check(root: Path, repos: list[tuple[str, str]], plugins: list[str]) -> None:
    if not repos:
        raise ValueError("name at least one repository (--repo NAME=OWNER)")
    for name, owner in repos:
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            raise ValueError(f"'{name}' must be a folder directly inside the workspace")
        if not owner.strip():
            raise ValueError(f"'{name}' needs an owner")
        if not (root / name / ".git").exists():
            raise ValueError(f"{root / name} is not the root of a git repository")
    for p in plugins:
        if not PLUGIN_ID.fullmatch(p):
            raise ValueError(f"'{p}' must be '<plugin>@<marketplace>'")


def _settings(plugins: list[str]) -> dict:
    secrets = load_policy("permissions")["secret_paths"]
    settings = {
        "$schema": SCHEMA,
        "permissions": {
            "allow": ["Read", "Grep", "Glob"] + [f"Bash({c})" for c in READ_ONLY_SHELL],
            "deny": [f"Read({p})" for p in secrets] + DENY_TOOLS,
            "disableBypassPermissionsMode": "disable"},
        "sandbox": {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False,
                    "autoAllowBashIfSandboxed": False,
                    "filesystem": {"denyRead": [p for s in secrets for p in _sandbox_paths(s)],
                                   "denyWrite": ["./"]},
                    "network": {"allowedDomains": []}},
        "autoMemoryEnabled": False,
    }
    if plugins:
        settings["enabledPlugins"] = {p: False for p in plugins}
    return settings


def init_workspace(root: Path, key: str, title: str, repos: list[tuple[str, str]],
                   disable_plugins: list[str]) -> list[tuple[str, str]]:
    _check(root, repos, disable_plugins)
    rows = "\n".join(f"| {name} | {owner} | <slice, role> | AGENTS.md |" for name, owner in repos)
    guide = render(load_template("workspace"), {"KEY": key, "TITLE": title}).replace(ROW_PLACEHOLDER, rows)
    report: list[tuple[str, str]] = []
    _write(root, "WORKSPACE.md", guide, report)
    _write(root, "CLAUDE.md", "<!-- Generated by aidlc workspace init. Edit WORKSPACE.md instead. -->\n"
                              "@WORKSPACE.md\n", report)
    _write(root, ".claude/settings.json", json.dumps(_settings(disable_plugins), indent=2) + "\n", report)
    return report
```

```python
# cli/aidlc/commands/workspace_cmd.py
"""aidlc workspace init: a workspace root with a read-only harness (never overwrites)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..cli import command
from ..policy import PolicyError
from ..workspace import init_workspace


def _run(args: argparse.Namespace) -> int:
    repos = []
    for spec in args.repo:
        name, sep, owner = spec.partition("=")
        if not sep:
            print(f"aidlc workspace init: --repo takes NAME=OWNER, got '{spec}'", file=sys.stderr)
            return 2
        repos.append((name.strip(), owner.strip()))
    try:
        report = init_workspace(Path(args.path).resolve(), args.key, args.title, repos, args.disable_plugin)
    except (ValueError, PolicyError) as exc:
        print(f"aidlc workspace init: {exc}", file=sys.stderr)
        return 2
    for rel, status in report:
        print(f"{status:18} {rel}")
    print("next: fill in WORKSPACE.md (each repository's slice and role) and commit it")
    return 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("workspace", help="set up a workspace root (read-only harness)")
    wsub = parser.add_subparsers(dest="workspace_command", metavar="<action>", required=True)
    init = wsub.add_parser("init", help="write WORKSPACE.md, CLAUDE.md and the read-only harness")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--key", required=True, help="the work item, e.g. SHIP-1")
    init.add_argument("--title", required=True)
    init.add_argument("--repo", action="append", required=True, metavar="NAME=OWNER")
    init.add_argument("--disable-plugin", action="append", default=[], metavar="PLUGIN@MARKETPLACE")
    init.set_defaults(func=_run)
```

Add `from . import workspace_cmd  # noqa: F401` to `cli/aidlc/commands/__init__.py` after `adopt_cmd`.

- [ ] **Step 4: Run the tests to see them pass**

Run: `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_workspace -v`
Expected: 6 tests OK.

- [ ] **Step 5: Document**

Write `docs/harness/workspace.md`: what a workspace root is (a folder holding repositories, plus `WORKSPACE.md`), when to start a session there (discovery and design across repositories) versus in a repository (all writing), what the read-only harness denies and why (`Edit`/`Write`, sandbox `denyWrite: ["./"]`, no auto-memory), `--disable-plugin` for user plugins that would interfere, the command line, and "never overwrites". Short sentences; one `> 🎯 **What this means for you:**` callout. Add a link line to `docs/harness/README.md` next to the root-guard entry.

- [ ] **Step 6: Gate and commit**

```bash
if make test > /tmp/claude-1000/-home-psharma-demos-aidlc/ddf15457-b666-4530-a462-8468c7639e9d/scratchpad/p6-t1.log 2>&1; then
  git add cli/aidlc/workspace.py cli/aidlc/commands/workspace_cmd.py cli/aidlc/commands/__init__.py \
          tests/unit/test_workspace.py docs/harness/workspace.md docs/harness/README.md
  git -c user.name=prashantsharma18 -c user.email=6386481+prashantsharma18@users.noreply.github.com \
      commit -m "feat(workspace): aidlc workspace init, a read-only harness for a workspace root" \
             -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
fi
```
Expected: `make test` OK, one commit.

---

### Task 2: `shipments-api` baseline (demo repository)

**Files (all under `~/work/shipment-tracking/shipments-api/`):**
- Create: `shipments-api.slnx`, `Directory.Build.props`, `.gitignore`, `.dockerignore`, `Dockerfile`
- Create: `api/openapi.yaml`
- Create: `src/ShipmentsApi/ShipmentsApi.csproj`, `src/ShipmentsApi/Program.cs`, `src/ShipmentsApi/Shipments.cs`
- Create: `tests/ShipmentsApi.Tests/ShipmentsApi.Tests.csproj`, `tests/ShipmentsApi.Tests/ShipmentEndpointTests.cs`, `tests/ShipmentsApi.Tests/ContractTests.cs`

**Interfaces:**
- Produces: `GET /shipments/{id}` → `{id, status, carrier, lastUpdated}` (contract 1.6.0), `GET /openapi.yaml`, `GET /healthz`; seeded `SHP-1001` (valid estimate), `SHP-1002` (none), `SHP-1003` (ends before it starts). The estimate is stored, not exposed: S2 exposes it.

- [ ] **Step 1: Scaffold**

```bash
mkdir -p ~/work/shipment-tracking && cd ~/work/shipment-tracking
git init -q -b main shipments-api && cd shipments-api
dotnet new sln -n shipments-api --format slnx
dotnet new web -n ShipmentsApi -o src/ShipmentsApi --framework net10.0
dotnet new xunit -n ShipmentsApi.Tests -o tests/ShipmentsApi.Tests --framework net10.0
dotnet sln add src/ShipmentsApi tests/ShipmentsApi.Tests
dotnet add tests/ShipmentsApi.Tests reference src/ShipmentsApi
dotnet add tests/ShipmentsApi.Tests package Microsoft.AspNetCore.Mvc.Testing
dotnet add tests/ShipmentsApi.Tests package YamlDotNet
dotnet new gitignore
```

`Directory.Build.props` (lock files make `dotnet restore --locked-mode` work):

```xml
<Project>
  <PropertyGroup>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>
  </PropertyGroup>
</Project>
```

In both `.csproj` files, link the contract into the output, so the app serves it and the tests read it:

```xml
<ItemGroup>
  <None Include="../../api/openapi.yaml" Link="openapi.yaml" CopyToOutputDirectory="PreserveNewest" CopyToPublishDirectory="PreserveNewest" />
</ItemGroup>
```

Delete the template's `UnitTest1.cs`.

- [ ] **Step 2: The contract**

```yaml
# api/openapi.yaml
openapi: 3.1.0
info:
  title: Shipments API
  version: 1.6.0
paths:
  /shipments/{id}:
    get:
      operationId: getShipment
      parameters:
        - {name: id, in: path, required: true, schema: {type: string}}
      responses:
        "200":
          description: The shipment.
          content:
            application/json:
              schema: {$ref: "#/components/schemas/Shipment"}
        "404":
          description: No shipment has this id.
components:
  schemas:
    Shipment:
      type: object
      additionalProperties: false
      required: [id, status, carrier, lastUpdated]
      properties:
        id: {type: string}
        status: {type: string, enum: [label_created, in_transit, out_for_delivery, delivered, exception]}
        carrier: {type: string}
        lastUpdated: {type: string, format: date-time}
```

- [ ] **Step 3: Write the failing tests**

```csharp
// tests/ShipmentsApi.Tests/ShipmentEndpointTests.cs
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace ShipmentsApi.Tests;

public sealed class ShipmentEndpointTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client = factory.CreateClient();

    [Fact]
    public async Task Known_shipment_returns_its_status_and_carrier()
    {
        var body = await _client.GetFromJsonAsync<JsonElement>("/shipments/SHP-1001");
        Assert.Equal("SHP-1001", body.GetProperty("id").GetString());
        Assert.Equal("in_transit", body.GetProperty("status").GetString());
        Assert.Equal("Northwind Freight", body.GetProperty("carrier").GetString());
    }

    [Fact]
    public async Task Unknown_shipment_is_404()
    {
        var response = await _client.GetAsync("/shipments/SHP-9999");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Lookup_ignores_case()
    {
        var response = await _client.GetAsync("/shipments/shp-1002");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task Encoded_id_is_404()
    {
        var response = await _client.GetAsync("/shipments/SHP-1001%20OR%201%3D1");
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Health_endpoint_answers()
    {
        var response = await _client.GetAsync("/healthz");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }
}
```

```csharp
// tests/ShipmentsApi.Tests/ContractTests.cs
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using YamlDotNet.RepresentationModel;

namespace ShipmentsApi.Tests;

/// <summary>The API's responses match api/openapi.yaml, the contract the portal team consumes.</summary>
public sealed class ContractTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    private static readonly string ContractPath = Path.Combine(AppContext.BaseDirectory, "openapi.yaml");

    [Theory]
    [InlineData("SHP-1001")]
    [InlineData("SHP-1002")]
    [InlineData("SHP-1003")]
    public async Task Response_matches_the_published_contract(string id)
    {
        var (declared, required) = ShipmentSchema();
        using var doc = JsonDocument.Parse(await factory.CreateClient().GetStringAsync($"/shipments/{id}"));
        var present = doc.RootElement.EnumerateObject().Select(p => p.Name).ToHashSet();
        Assert.Subset(declared, present);    // no property the contract does not declare
        Assert.Superset(required, present);  // every required property is there
    }

    [Fact]
    public async Task Served_contract_is_the_repository_contract()
    {
        var served = await factory.CreateClient().GetStringAsync("/openapi.yaml");
        Assert.Equal(await File.ReadAllTextAsync(ContractPath), served);
    }

    private static (HashSet<string> Declared, HashSet<string> Required) ShipmentSchema()
    {
        var yaml = new YamlStream();
        using (var reader = File.OpenText(ContractPath)) yaml.Load(reader);
        var root = (YamlMappingNode)yaml.Documents[0].RootNode;
        var shipment = Map(Map(Map(root, "components"), "schemas"), "Shipment");
        var declared = Map(shipment, "properties").Children.Keys
            .Select(k => ((YamlScalarNode)k).Value!).ToHashSet();
        var required = ((YamlSequenceNode)shipment.Children[new YamlScalarNode("required")]).Children
            .Select(n => ((YamlScalarNode)n).Value!).ToHashSet();
        return (declared, required);
    }

    private static YamlMappingNode Map(YamlMappingNode node, string key) =>
        (YamlMappingNode)node.Children[new YamlScalarNode(key)];
}
```

Run: `dotnet test --nologo`
Expected: build FAILS (`Program`, the endpoints and the store do not exist yet).

- [ ] **Step 4: Implement**

```csharp
// src/ShipmentsApi/Shipments.cs
using System.Globalization;

namespace ShipmentsApi;

/// <summary>The carrier's delivery estimate, as the carrier sends it (not validated).</summary>
public sealed record CarrierEstimate(DateTimeOffset Earliest, DateTimeOffset Latest);

public sealed record Shipment(string Id, string Status, string Carrier, DateTimeOffset LastUpdated,
                              CarrierEstimate? Estimate);

/// <summary>The public shape of a shipment: contract 1.6.0.</summary>
public sealed record ShipmentView(string Id, string Status, string Carrier, DateTimeOffset LastUpdated)
{
    public static ShipmentView From(Shipment s) => new(s.Id, s.Status, s.Carrier, s.LastUpdated);
}

public interface IShipmentStore
{
    Shipment? Find(string id);
}

/// <summary>Seed data standing in for the shipments database and the carrier feed.</summary>
public sealed class InMemoryShipmentStore : IShipmentStore
{
    private static readonly Dictionary<string, Shipment> Seed = new(StringComparer.OrdinalIgnoreCase)
    {
        ["SHP-1001"] = new("SHP-1001", "in_transit", "Northwind Freight", At("2026-10-22T09:15:00Z"),
            new CarrierEstimate(At("2026-10-24T09:00:00Z"), At("2026-10-24T13:00:00Z"))),
        ["SHP-1002"] = new("SHP-1002", "label_created", "Contoso Parcel", At("2026-10-23T07:40:00Z"), null),
        // The carrier sent a window that ends before it starts.
        ["SHP-1003"] = new("SHP-1003", "in_transit", "Fabrikam Logistics", At("2026-10-22T18:05:00Z"),
            new CarrierEstimate(At("2026-10-25T17:00:00Z"), At("2026-10-25T08:00:00Z"))),
    };

    public Shipment? Find(string id) => Seed.GetValueOrDefault(id);

    private static DateTimeOffset At(string iso) => DateTimeOffset.Parse(iso, CultureInfo.InvariantCulture);
}
```

```csharp
// src/ShipmentsApi/Program.cs
using ShipmentsApi;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<IShipmentStore, InMemoryShipmentStore>();

var app = builder.Build();

app.MapGet("/shipments/{id}", (string id, IShipmentStore store) =>
    store.Find(id) is { } shipment ? Results.Ok(ShipmentView.From(shipment)) : Results.NotFound());

app.MapGet("/openapi.yaml", () =>
    Results.File(Path.Combine(AppContext.BaseDirectory, "openapi.yaml"), "application/yaml"));

app.MapGet("/healthz", () => Results.Ok());

app.Run();

public partial class Program;
```

- [ ] **Step 5: Run the tests and the format check**

Run: `dotnet format && dotnet build --nologo -warnaserror && dotnet test --nologo`
Expected: build with 0 warnings; 9 tests pass. Fix warnings in the code, never by suppressing them.

- [ ] **Step 6: Container**

```dockerfile
# Dockerfile
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY . .
RUN dotnet restore src/ShipmentsApi/ShipmentsApi.csproj --locked-mode \
 && dotnet publish src/ShipmentsApi/ShipmentsApi.csproj -c Release --no-restore -o /app

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app .
ENV ASPNETCORE_HTTP_PORTS=8080
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "ShipmentsApi.dll"]
```

`.dockerignore`: `**/bin`, `**/obj`, `.check`, `.git`, `tests`.

Run: `docker build -t shipments-api:1.6.0 . && docker run --rm -d -p 8081:8080 --name api-smoke shipments-api:1.6.0 && sleep 3 && curl -s localhost:8081/shipments/SHP-1001; docker stop api-smoke`
Expected: `{"id":"SHP-1001","status":"in_transit","carrier":"Northwind Freight","lastUpdated":"2026-10-22T09:15:00+00:00"}`.

- [ ] **Step 7: Commit**

```bash
git add -A && git -c user.name=prashantsharma18 -c user.email=6386481+prashantsharma18@users.noreply.github.com \
  commit -q -m "baseline: shipments API 1.6.0 (written outside the harness; plays the existing product)" \
            -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git tag api-v1.6.0
```

---

### Task 3: `customer-portal` baseline (demo repository)

**Files (all under `~/work/shipment-tracking/customer-portal/`):**
- Scaffold: Vite `react-ts` template
- Create: `.nvmrc`, `src/api/shipments.ts`, `src/flags.tsx`, `src/ShipmentLookup.tsx`, `src/App.tsx`, `src/main.tsx`, `src/test/setup.ts`
- Create: `src/api/shipments.test.ts`, `src/flags.test.tsx`, `src/ShipmentLookup.test.tsx`
- Create: `Dockerfile`, `.dockerignore`, `nginx.conf`, `docker/40-flags.sh`
- Modify: `package.json` (scripts), `vite.config.ts` (test and dev proxy)

**Interfaces:**
- Consumes: Task 2's `GET /shipments/{id}` (through `/api` on the same origin).
- Produces: `getShipment(id, fetchFn?) : Promise<Shipment>`, `ShipmentNotFoundError`, `FlagsProvider`, `loadFlags(fetchFn) : Promise<Record<string, boolean>>`, `useFlag(name) : boolean`, runtime `/config.json` = `{"flags": {"<name>": bool}}` from `FLAG_<NAME>` environment variables.

- [ ] **Step 1: Scaffold**

```bash
cd ~/work/shipment-tracking
source ~/.nvm/nvm.sh && nvm use 22
npm create vite@6 customer-portal -- --template react-ts
cd customer-portal && git init -q -b main && echo "22" > .nvmrc
npm install
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Use the `create-vite` major version that `npm view create-vite version` reports if 6 is not current; record which in the commit message. Delete the template's `App.css`, `assets/` and demo content.

`package.json` scripts:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "typecheck": "tsc -b",
  "test": "vitest run --reporter=default --reporter=json --outputFile.json=.check/test-report.json",
  "preview": "vite preview"
}
```

`vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // In development the API runs in its container on :8081; production uses the nginx proxy.
    proxy: { "/api": { target: "http://localhost:8081", rewrite: (path) => path.replace(/^\/api/, "") } },
  },
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"] },
});
```

`src/test/setup.ts`: `import "@testing-library/jest-dom/vitest";`. Add `.check/` to `.gitignore`.

- [ ] **Step 2: Write the failing tests**

```ts
// src/api/shipments.test.ts
import { describe, expect, it, vi } from "vitest";
import { getShipment, ShipmentNotFoundError } from "./shipments";

const shipment = { id: "SHP-1001", status: "in_transit", carrier: "Northwind Freight",
                   lastUpdated: "2026-10-22T09:15:00+00:00" };

function respond(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue(new Response(body === undefined ? null : JSON.stringify(body), { status }));
}

describe("getShipment", () => {
  it("returns the shipment", async () => {
    const fetchFn = respond(200, shipment);
    await expect(getShipment("SHP-1001", fetchFn)).resolves.toEqual(shipment);
    expect(fetchFn).toHaveBeenCalledWith("/api/shipments/SHP-1001", { headers: { Accept: "application/json" } });
  });

  it("encodes the id", async () => {
    const fetchFn = respond(404);
    await expect(getShipment("a/b c", fetchFn)).rejects.toBeInstanceOf(ShipmentNotFoundError);
    expect(fetchFn.mock.calls[0][0]).toBe("/api/shipments/a%2Fb%20c");
  });

  it("throws ShipmentNotFoundError on 404", async () => {
    await expect(getShipment("SHP-9999", respond(404))).rejects.toBeInstanceOf(ShipmentNotFoundError);
  });

  it("throws on any other failure", async () => {
    await expect(getShipment("SHP-1001", respond(503))).rejects.toThrow("Shipments API returned 503");
  });
});
```

```tsx
// src/flags.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FlagsProvider, loadFlags, useFlag } from "./flags";

const config = (body: string, status = 200) => vi.fn().mockResolvedValue(new Response(body, { status }));

function Probe() {
  return <p>{useFlag("show-delivery-window") ? "on" : "off"}</p>;
}

describe("flags", () => {
  it("the provider exposes a flag from /config.json", async () => {
    render(<FlagsProvider fetchFn={config(JSON.stringify({ flags: { "show-delivery-window": true } }))}>
      <Probe /></FlagsProvider>);
    expect(await screen.findByText("on")).toBeInTheDocument();
  });

  it("missing config means every flag is off", async () => {
    await expect(loadFlags(config("", 404))).resolves.toEqual({});
  });

  it("malformed config means every flag is off", async () => {
    await expect(loadFlags(config("not json"))).resolves.toEqual({});
  });

  it("a non-boolean value is off", async () => {
    await expect(loadFlags(config(JSON.stringify({ flags: { a: "true", b: true } })))).resolves.toEqual({ b: true });
  });
});
```

```tsx
// src/ShipmentLookup.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ShipmentNotFoundError } from "./api/shipments";
import { ShipmentLookup } from "./ShipmentLookup";

const shipment = { id: "SHP-1001", status: "in_transit" as const, carrier: "Northwind Freight",
                   lastUpdated: "2026-10-22T09:15:00+00:00" };

async function track(load: (id: string) => Promise<typeof shipment>, id = "SHP-1001") {
  render(<ShipmentLookup load={load} />);
  await userEvent.type(screen.getByLabelText("Shipment number"), id);
  await userEvent.click(screen.getByRole("button", { name: "Track" }));
}

describe("ShipmentLookup", () => {
  it("shows the status and carrier", async () => {
    await track(vi.fn().mockResolvedValue(shipment));
    expect(await screen.findByText("In transit")).toBeInTheDocument();
    expect(screen.getByText("Northwind Freight")).toBeInTheDocument();
  });

  it("trims the id before loading", async () => {
    const load = vi.fn().mockResolvedValue(shipment);
    await track(load, "  SHP-1001 ");
    expect(load).toHaveBeenCalledWith("SHP-1001");
  });

  it("says when no shipment has the number", async () => {
    await track(vi.fn().mockRejectedValue(new ShipmentNotFoundError("SHP-9999")), "SHP-9999");
    expect(await screen.findByRole("alert")).toHaveTextContent("No shipment SHP-9999");
  });

  it("says when the service fails", async () => {
    await track(vi.fn().mockRejectedValue(new Error("Shipments API returned 503")));
    expect(await screen.findByRole("alert")).toHaveTextContent("Tracking is unavailable");
  });
});
```

Run: `npm test`
Expected: FAIL, the modules `./shipments`, `./flags`, `./ShipmentLookup` do not exist.

- [ ] **Step 3: Implement**

```ts
// src/api/shipments.ts
/** The Shipments API client, written against contract 1.6.0 (api/openapi.yaml in shipments-api). */
export type ShipmentStatus = "label_created" | "in_transit" | "out_for_delivery" | "delivered" | "exception";

export interface Shipment {
  id: string;
  status: ShipmentStatus;
  carrier: string;
  lastUpdated: string;
}

export class ShipmentNotFoundError extends Error {
  constructor(readonly id: string) {
    super(`No shipment ${id}`);
    this.name = "ShipmentNotFoundError";
  }
}

export async function getShipment(id: string, fetchFn: typeof fetch = fetch): Promise<Shipment> {
  const response = await fetchFn(`/api/shipments/${encodeURIComponent(id)}`, {
    headers: { Accept: "application/json" },
  });
  if (response.status === 404) throw new ShipmentNotFoundError(id);
  if (!response.ok) throw new Error(`Shipments API returned ${response.status}`);
  return (await response.json()) as Shipment;
}
```

```tsx
// src/flags.tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

/** Runtime flags from /config.json, written at container start from FLAG_* variables. Unknown means off. */
type Flags = Record<string, boolean>;

const FlagsContext = createContext<Flags>({});

export async function loadFlags(fetchFn: typeof fetch): Promise<Flags> {
  try {
    const response = await fetchFn("/config.json", { cache: "no-store" });
    if (!response.ok) return {};
    const body: unknown = await response.json();
    const flags = (body as { flags?: unknown })?.flags;
    if (typeof flags !== "object" || flags === null) return {};
    return Object.fromEntries(Object.entries(flags).filter(([, v]) => v === true));
  } catch {
    return {};
  }
}

export function FlagsProvider({ children, fetchFn = fetch }: { children: ReactNode; fetchFn?: typeof fetch }) {
  const [flags, setFlags] = useState<Flags>({});
  useEffect(() => {
    let live = true;
    void loadFlags(fetchFn).then((loaded) => { if (live) setFlags(loaded); });
    return () => { live = false; };
  }, [fetchFn]);
  return <FlagsContext.Provider value={flags}>{children}</FlagsContext.Provider>;
}

export function useFlag(name: string): boolean {
  return useContext(FlagsContext)[name] === true;
}
```

```tsx
// src/ShipmentLookup.tsx
import { useState, type FormEvent } from "react";
import { getShipment, ShipmentNotFoundError, type Shipment, type ShipmentStatus } from "./api/shipments";

const STATUS_LABELS: Record<ShipmentStatus, string> = {
  label_created: "Label created",
  in_transit: "In transit",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  exception: "Delivery problem",
};

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "found"; shipment: Shipment }
  | { kind: "error"; message: string };

export function ShipmentLookup({ load = getShipment }: { load?: (id: string) => Promise<Shipment> }) {
  const [id, setId] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const wanted = id.trim();
    if (!wanted) return;
    setState({ kind: "loading" });
    try {
      setState({ kind: "found", shipment: await load(wanted) });
    } catch (error) {
      setState({ kind: "error", message: error instanceof ShipmentNotFoundError
        ? `No shipment ${error.id}. Check the number on your confirmation email.`
        : "Tracking is unavailable right now. Please try again in a few minutes." });
    }
  }

  return (
    <section>
      <form onSubmit={onSubmit}>
        <label htmlFor="shipment-id">Shipment number</label>
        <input id="shipment-id" value={id} onChange={(e) => setId(e.target.value)} placeholder="SHP-1001" />
        <button type="submit" disabled={state.kind === "loading"}>Track</button>
      </form>
      {state.kind === "error" && <p role="alert">{state.message}</p>}
      {state.kind === "found" && (
        <dl>
          <dt>Status</dt><dd>{STATUS_LABELS[state.shipment.status] ?? state.shipment.status}</dd>
          <dt>Carrier</dt><dd>{state.shipment.carrier}</dd>
          <dt>Last update</dt>
          <dd>{new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" })
                .format(new Date(state.shipment.lastUpdated))}</dd>
        </dl>
      )}
    </section>
  );
}
```

```tsx
// src/App.tsx
import { ShipmentLookup } from "./ShipmentLookup";

export default function App() {
  return (
    <main>
      <h1>Track your shipment</h1>
      <ShipmentLookup />
    </main>
  );
}
```

```tsx
// src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { FlagsProvider } from "./flags";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <FlagsProvider>
      <App />
    </FlagsProvider>
  </StrictMode>,
);
```

Replace `src/index.css` with a short, plain stylesheet (system font, a centred 40rem column, readable form spacing).

- [ ] **Step 4: Run every check**

Run: `npm run lint && npm run typecheck && npm test && npm run build`
Expected: all pass; 12 tests; `.check/test-report.json` written.

- [ ] **Step 5: Container and the flag script**

```sh
#!/bin/sh
# docker/40-flags.sh — writes the runtime flags the portal reads from /config.json.
# FLAG_SHOW_DELIVERY_WINDOW=true becomes "show-delivery-window": true. Anything but "true" is false.
set -eu
entries=""
for name in $(env | grep -E '^FLAG_[A-Z0-9_]+=' | cut -d= -f1); do
  flag=$(printf '%s' "${name#FLAG_}" | tr 'A-Z_' 'a-z-')
  eval "value=\${$name}"
  if [ "$value" = "true" ]; then v=true; else v=false; fi
  entries="${entries:+$entries, }\"$flag\": $v"
done
printf '{"flags": {%s}}\n' "$entries" > /tmp/config.json
```

```nginx
# nginx.conf
server {
    listen 8080;
    root /usr/share/nginx/html;

    location /api/ {
        proxy_pass http://shipments-api:8080/;
    }

    location = /config.json {
        alias /tmp/config.json;
        add_header Cache-Control "no-store";
    }

    location / {
        try_files $uri /index.html;
    }
}
```

```dockerfile
# Dockerfile
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=0755 docker/40-flags.sh /docker-entrypoint.d/40-flags.sh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
```

`.dockerignore`: `node_modules`, `dist`, `.check`, `.git`.

Flag script check (Review Focus 3):

```bash
env -i sh docker/40-flags.sh && cat /tmp/config.json
env -i FLAG_SHOW_DELIVERY_WINDOW=true FLAG_OTHER=yes sh docker/40-flags.sh && python3 -m json.tool /tmp/config.json
```
Expected: `{"flags": {}}`, then valid JSON with `"show-delivery-window": true` and `"other": false`.

Run: `docker build -t customer-portal:baseline .`
Expected: image builds.

- [ ] **Step 6: Commit**

```bash
git add -A && git -c user.name=prashantsharma18 -c user.email=6386481+prashantsharma18@users.noreply.github.com \
  commit -q -m "baseline: customer portal, shipment lookup and runtime flags (written outside the harness)" \
            -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The workspace, onboarding and the running app

**Files (under `~/work/shipment-tracking/`):**
- Create: `.gitignore`, `compose.yaml`, `flags.env`; generated `WORKSPACE.md`, `CLAUDE.md`, `.claude/settings.json`
- Each repository: `aidlc init-repo` output, edited `.aidlc/config.yaml`, filled `AGENTS.md` and `docs/codebase-map.md`, rendered files

**Interfaces:**
- Consumes: Task 1's `aidlc workspace init`; Tasks 2 and 3's images.
- Produces: a running app at <http://localhost:8080>; both repositories pass `aidlc check` on `main`.

- [ ] **Step 1: The workspace repository**

```bash
cd ~/work/shipment-tracking && git init -q -b main
printf '/shipments-api/\n/customer-portal/\n' > .gitignore
~/demos/aidlc/bin/aidlc workspace init . --key SHIP-1 --title "Show customers an estimated delivery window" \
  --repo "shipments-api=Logistics team" --repo "customer-portal=Web team" \
  $(for p in superpowers@claude-plugins-official skill-creator@claude-plugins-official platform@ai-assets \
             baseline@local discovery-pack@local spec-pack@local impl-pack@local governance-pack@local; do
      printf -- '--disable-plugin %s ' "$p"; done)
```

Fill in the slice and role cells of `WORKSPACE.md` (S1, S2 provider in shipments-api; S3 consumer in customer-portal). Point the coordination plan line at `shipments-api/plans/SHIP-1/coordination-plan.md`.

```yaml
# compose.yaml
name: shipment-tracking
services:
  shipments-api:
    image: shipments-api:${API_TAG:-1.6.0}
    build: ./shipments-api
    env_file: flags.env
    ports: ["8081:8080"]
  customer-portal:
    image: customer-portal:${PORTAL_TAG:-baseline}
    build: ./customer-portal
    env_file: flags.env
    ports: ["8080:8080"]
    depends_on: [shipments-api]
```

```bash
# flags.env
# The demo's flag service. A person changes a flag here, then restarts the containers:
#   docker compose up -d --force-recreate
# Portal flags: FLAG_<NAME>=true|false   (served to the browser as /config.json)
# API flags:    Flags__<Name>=true|false (ASP.NET configuration)
```

- [ ] **Step 2: Onboard each repository**

```bash
cd ~/work/shipment-tracking/shipments-api
~/demos/aidlc/bin/aidlc init-repo . --name shipments-api --owner "Logistics team" --profile dotnet \
  --purpose "Shipment status for customers and partners; owns the Shipments API contract (api/openapi.yaml)"
cd ../customer-portal
~/demos/aidlc/bin/aidlc init-repo . --name customer-portal --owner "Web team" --profile node \
  --purpose "The customer-facing tracking site; consumes the Shipments API"
```

In each `.aidlc/config.yaml`, set `harness.disable_user_plugins` to the eight plugins in Global Constraints. Fill `AGENTS.md` and `docs/codebase-map.md` for real (layout, commands, the contract, the flags mechanism, the test layout). The `dotnet` profile's `format` step needs `dotnet format`; the `node` profile's commands match Task 3's scripts.

- [ ] **Step 3: Map the tracker tools**

Find lab-jira's tool names from a session's init message (no tool runs):

```bash
cd ~/work/shipment-tracking/shipments-api
claude -p "Reply OK." --setting-sources project,local --output-format stream-json --verbose --max-turns 1 \
  | head -1 | python3 -c "import json,sys; print('\n'.join(t for t in json.load(sys.stdin)['tools'] if 'jira' in t.lower()))"
```

Set `tool_names` in both configs: `tracker.read_issue`, `tracker.search`, `tracker.add_comment`, `tracker.create_issue`, `tracker.transition_issue` and `tracker.delete_*` to the matching `mcp__lab-jira__…` names. If lab-jira does not appear with `--setting-sources project,local`, record finding F-mcp and pass it with `--mcp-config` from the user's existing definition, without printing its URL.

- [ ] **Step 4: Render, check, commit**

```bash
for r in shipments-api customer-portal; do
  cd ~/work/shipment-tracking/$r
  ~/demos/aidlc/bin/aidlc render --tool claude-code && ~/demos/aidlc/bin/aidlc check && \
  git add -A && git -c user.name=prashantsharma18 -c user.email=6386481+prashantsharma18@users.noreply.github.com \
    commit -q -m "chore: adopt aidlc (Procedure A), harness for Claude Code" \
              -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
done
cd ~/work/shipment-tracking && git add -A && git -c user.name=prashantsharma18 \
  -c user.email=6386481+prashantsharma18@users.noreply.github.com commit -q \
  -m "workspace: shipment-tracking (WORKSPACE.md, read-only harness, compose, flags)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `aidlc check` passes in both repositories. A failure is fixed in the repository (or recorded as a framework finding), never skipped.

- [ ] **Step 5: Run the app**

```bash
cd ~/work/shipment-tracking && docker compose up -d --build
sleep 5; curl -s localhost:8080/api/shipments/SHP-1001; echo; curl -s localhost:8080/config.json
```
Expected: the SHP-1001 JSON through the portal's proxy, and `{"flags": {}}`. Tell the user: open <http://localhost:8080> and track `SHP-1001`.

- [ ] **Step 6: Trust the three folders (user)**

Unattended sessions need trusted folders (`docs/harness/permissions-and-sandbox.md`). Ask the user to run `claude` once in each of `~/work/shipment-tracking`, `…/shipments-api` and `…/customer-portal`, accept the trust prompt, and exit. Do not edit `~/.claude.json` without their explicit go-ahead.

---

### Task 5: The clean-harness probe

**Files:**
- Create: `~/demos/aidlc/docs/demo/probe.py` (reads a stream-json init line from stdin, prints the verdict)

**Interfaces:**
- Produces: `python3 docs/demo/probe.py < init.json` → exit 0 and `clean` when the only plugins are `aidlc` and `aidlc-practice`; exit 1 listing anything else.

- [ ] **Step 1: The probe script**

```python
#!/usr/bin/env python3
"""Clean-harness probe for the demo: reads Claude Code's stream-json init message on stdin and
fails if anything but the aidlc plugins loaded. Usage: claude -p … --output-format stream-json
--verbose --max-turns 1 | head -1 | python3 docs/demo/probe.py"""
import json
import sys

ALLOWED_PLUGINS = {"aidlc", "aidlc-practice"}


def main() -> int:
    init = json.loads(sys.stdin.readline())
    plugins = {p["name"] if isinstance(p, dict) else str(p) for p in init.get("plugins", [])}
    skills = init.get("skills") or init.get("slash_commands") or []
    foreign_plugins = sorted(plugins - ALLOWED_PLUGINS)
    foreign_skills = sorted(s for s in skills if ":" in s and s.split(":", 1)[0] not in ALLOWED_PLUGINS)
    print("plugins:", sorted(plugins))
    print("mcp servers:", sorted(m.get("name", "?") for m in init.get("mcp_servers", [])))
    if foreign_plugins or foreign_skills:
        print("NOT CLEAN:", foreign_plugins + foreign_skills)
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Probe the three folders**

```bash
for d in ~/work/shipment-tracking ~/work/shipment-tracking/shipments-api ~/work/shipment-tracking/customer-portal; do
  (cd "$d" && claude -p "Reply OK." --setting-sources project,local \
     --plugin-dir ~/demos/aidlc/plugins/aidlc --plugin-dir ~/demos/aidlc/plugins/aidlc-practice \
     --output-format stream-json --verbose --max-turns 1 | head -1 | python3 ~/demos/aidlc/docs/demo/probe.py)
done
```
Expected: `clean` three times, lab-jira among the MCP servers. Also run each folder once **without** `--setting-sources` (as the user would in VS Code) and expect `clean`: that proves `disable_user_plugins` works for interactive sessions.

- [ ] **Step 3: Ask about instructions and probe a block**

In each folder: `claude -p "List every CLAUDE.md or memory file whose content is in your context, by path. Then try to create the file plans/probe.md containing 'x'." --setting-sources project,local --plugin-dir … --permission-mode dontAsk` with `AIDLC_UNATTENDED=1`.
Expected: only the folder's own `CLAUDE.md` (and in the workspace, `WORKSPACE.md` through it); the write is denied (the repositories: `plans/**` is protected; the workspace: every write is denied). Save the outputs to `docs/demo/evidence/` for Task 8.

- [ ] **Step 4: Commit the probe**

Framework commit of `docs/demo/probe.py` and the evidence, gated by `make test`. Any "NOT CLEAN" result is a finding, fixed before Task 6.

---

### Task 6: SHIP-1 through design, plan and build

Each stage is one headless session (`S` below means the Global Constraints command). A stage that asks questions is continued with `claude -p --resume <session_id> "<the user's answers>"`. At every gate, the driver shows the user the draft and waits for "approved" or changes. The driver saves an approved draft and commits it with "saved by the driver after the user's approval".

- [ ] **Step 1: Intent and spec** (in `shipments-api`, the contract owner): `S "/aidlc:aidlc-intent SHIP-1"`, then `S "/aidlc:aidlc-specify SHIP-1"`. Gate: the user approves each. Save to `plans/SHIP-1/intent.md` and `plans/SHIP-1/spec.md` on branch `feat/SHIP-1-delivery-window`.
- [ ] **Step 2: Discover** (workspace root, read-only): `S "/aidlc:aidlc-discover SHIP-1: who reads or writes the shipment shape, and what breaks if a field is added"`. Gate: the user sets the tier and decides proceed or escalate.
- [ ] **Step 3: Design** (workspace root): `S "/aidlc:aidlc-design SHIP-1"`. Expect a contract-first design: OpenAPI 1.7.0, the consumer test, the ADR. Gate: the user approves against the six checks; the driver records the APPROVED line.
- [ ] **Step 4: Plan** (each repository): `S "/aidlc:aidlc-plan SHIP-1"` in `shipments-api` (S1, S2 and the coordination plan) and in `customer-portal` (S3). Gate: the user approves the plans and the task bundles; the driver saves them and adds each bundle to `plans/approved-bundles.txt`.
- [ ] **Step 5: Build S1 and S2** (`shipments-api`): `S "/aidlc:aidlc-build-slice SHIP-1 S1"` (the driver first runs the `aidlc scope` command the skill names, as the person would); then S2. After S1 is merged into the story branch, the driver tags `api-v1.7.0`. Expect at least one hook decision in `decisions.jsonl`; record it.
- [ ] **Step 6: Build S3** (`customer-portal`): as Step 5 with S3, from the pinned `api-v1.7.0` contract.
- [ ] **Step 7: Verify and review** (each repository): `S "/aidlc:aidlc-verify SHIP-1"`, then `S "/aidlc:aidlc-review SHIP-1"`. Gate: the user signs the review record. Run `aidlc check` and `aidlc ci` (local preview) on each story branch; both pass.

Expected for the task: every artefact is saved in its repository, every gate has an approval line, and both story branches are green.

---

### Task 7: The compatibility matrix, the release and the aftermath

- [ ] **Step 1: Images.** Build `shipments-api:1.7.0` and `customer-portal:SHIP-1` from the story branches.
- [ ] **Step 2: The matrix.** For each of the four pairs (`API_TAG` 1.6.0 or 1.7.0 × `PORTAL_TAG` baseline or SHIP-1), with both flags on and then off: `docker compose up -d --force-recreate`, then check `/api/shipments/SHP-1001`, `SHP-1002` and `SHP-1003` through the portal and the page for SHP-1001. Expected: no pair breaks. The window shows only for new API + new portal + both flags on + SHP-1001. Fill `compat-matrix.md` (saved in `shipments-api/plans/SHIP-1/`).
- [ ] **Step 3: Release.** `S "/aidlc:aidlc-release SHIP-1"`. Gate: the user approves ship. The driver rolls out the new images, turns on `Flags__EtaInApi`, then `FLAG_SHOW_DELIVERY_WINDOW`, and tells the user to open <http://localhost:8080> and track SHP-1001, SHP-1002 and SHP-1003.
- [ ] **Step 4: Operate.** Simulate an incident (labelled): a carrier feed window in the wrong time zone, reported by a customer. `S "/aidlc:aidlc-operate SHIP-1 <report>"`. The user runs the queries the diagnoser names; containment is a flag flip, done by the driver after the user chooses it.
- [ ] **Step 5: Feedback.** `S "/aidlc:aidlc-feedback SHIP-1"`. Each lesson is routed to a layer; the drafts are saved after approval.

---

### Task 8: Evidence, runbook and findings

**Files (framework):**
- Create: `docs/demo/shipment-tracking.md` (replay runbook: Tasks 2–7 as commands, with what to expect)
- Create: `docs/verification/<run date>-shipment-tracking-demo.md` (what ran, every gate and its approval, every hook block, what was simulated, the matrix, the findings)
- Modify: framework files named by each finding, test first

- [ ] **Step 1:** Write the findings list: ID, what happened, layer, fix or ruling.
- [ ] **Step 2:** Fix each framework finding with a failing test first, one commit each, `make test` green.
- [ ] **Step 3:** Write the runbook and the evidence page; link both from the top-level `README.md` docs list.
- [ ] **Step 4:** Final gate: `make test`, `AIDLC_TOOLS_DIR=<scratchpad>/tools-live make policy-test`, `bin/aidlc trace --check`, `bin/aidlc policy validate`, `bin/aidlc plugin build --check`. Commit.
- [ ] **Step 5:** Whole-branch review of the framework changes (fresh reviewer), one fix pass, then report to the user. The app stays running at <http://localhost:8080>.
