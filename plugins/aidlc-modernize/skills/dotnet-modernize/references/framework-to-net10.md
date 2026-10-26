# .NET Framework 4.x to .NET 10: breaking changes and their fixes

Each row: what breaks, the usual fix, and the test that proves the fix kept behaviour. Every fix is its own step,
tests first. Packages are dependency decisions for the person.

| What breaks | Usual fix | Prove it with |
|---|---|---|
| `BinaryFormatter` was removed in .NET 9: `Serialize` and `Deserialize` throw `PlatformNotSupportedException`. | Replace with System.Text.Json or another explicit format. Files written by the old version are a one-way door: decide migrate, rebuild (fine for a cache) or keep a reader. The unsupported compatibility package that restores it is an owner decision, never a quiet fix. | A test that round-trips the new format; a test of what happens to an old file (the decided behaviour). |
| `System.Configuration.ConfigurationManager` is not part of .NET. | Either the `System.Configuration.ConfigurationManager` package (reads `App.config`, copied as `<app>.dll.config`) or `Microsoft.Extensions.Configuration` (a design change). Both are dependency decisions. | The characterisation tests that read settings; a test that a missing setting fails the way it did. |
| AppDomains (beyond the current one), .NET Remoting and Code Access Security are not supported. | Processes or containers for isolation; gRPC or HTTP for remote calls; remove CAS attributes. | The behaviour the isolation protected, tested at the new boundary. |
| `WebClient` and `WebRequest` are obsolete (SYSLIB0014). | `HttpClient`, created once and reused. | Tests with a stub handler: same requests, same error handling. |
| `System.Drawing.Common` is Windows-only. | An image library that runs on Linux, or keep Windows hosting (a decision). | Image output compared on sample inputs. |
| Globalisation on Linux uses ICU, not Windows NLS: culture-sensitive formatting, parsing and string comparison can differ. | Pin the culture where output is data (`CultureInfo.InvariantCulture`); review every `ToString()` and `Parse` without a culture. | Parity on Linux against the Windows run; tests for each number and date format. |
| `Math.Round` defaults to rounding half to even, as before. | Keep it unless the owner decides otherwise; never "fix" it during the port. | A characterisation test on a midpoint value. |
| Windows-only APIs (registry, event log, WMI) raise analyzer CA1416. | Abstract them behind an interface, or keep Windows hosting (a decision). | Tests of the interface on both sides. |
| Default file paths and line endings differ on Linux. | `Path.Combine`, no hard-coded separators; compare output after normalising line endings. | Parity normalises CRLF; tests for path handling. |

Facts that set the target: .NET 10 is the current LTS; .NET 8 support ends on 10 November 2026.
