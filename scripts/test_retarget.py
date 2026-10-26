"""Tests for plugins/aidlc-modernize/skills/dotnet-modernize/scripts/retarget.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins" / "aidlc-modernize" / "skills"
                       / "dotnet-modernize" / "scripts"))
import retarget  # noqa: E402

LEGACY = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net48</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NETFramework.ReferenceAssemblies" Version="1.0.3" PrivateAssets="all" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="xunit.v3" Version="2.0.3" />
  </ItemGroup>
</Project>
"""


class RetargetTest(unittest.TestCase):
    def test_changes_the_target_and_drops_the_reference_assemblies(self):
        out = retarget.retarget(LEGACY, "net48", "net10.0")
        self.assertIn("<TargetFramework>net10.0</TargetFramework>", out)
        self.assertNotIn("Microsoft.NETFramework.ReferenceAssemblies", out)
        self.assertIn('Include="xunit.v3"', out)
        self.assertEqual(out.count("<ItemGroup>"), 1)

    def test_multi_targeting_swaps_only_the_old_framework(self):
        text = LEGACY.replace("<TargetFramework>net48</TargetFramework>",
                              "<TargetFrameworks>net48;net8.0</TargetFrameworks>")
        self.assertIn("<TargetFrameworks>net10.0;net8.0</TargetFrameworks>", retarget.retarget(text, "net48", "net10.0"))

    def test_a_second_run_changes_nothing(self):
        once = retarget.retarget(LEGACY, "net48", "net10.0")
        self.assertEqual(retarget.retarget(once, "net48", "net10.0"), once)

    def test_an_old_style_project_is_refused(self):
        with self.assertRaises(ValueError):
            retarget.retarget('<Project ToolsVersion="15.0"><PropertyGroup/></Project>', "net48", "net10.0")

    def test_a_project_targeting_neither_is_refused(self):
        with self.assertRaises(ValueError):
            retarget.retarget(LEGACY.replace("net48", "net472"), "net48", "net10.0")

    def test_crlf_and_bom_are_kept_and_nothing_is_written_on_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, "a.csproj"), Path(tmp, "b.csproj")
            good.write_bytes(b"\xef\xbb\xbf" + LEGACY.replace("\n", "\r\n").encode())
            bad.write_text('<Project ToolsVersion="15.0"/>')
            self.assertEqual(retarget.main(["retarget.py", "--from", "net48", "--to", "net10.0", str(good), str(bad)]), 1)
            self.assertIn(b"net48", good.read_bytes())
            self.assertEqual(retarget.main(["retarget.py", "--from", "net48", "--to", "net10.0", str(good)]), 0)
            data = good.read_bytes()
            self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"<TargetFramework>net10.0</TargetFramework>\r\n", data)
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))


if __name__ == "__main__":
    unittest.main()
