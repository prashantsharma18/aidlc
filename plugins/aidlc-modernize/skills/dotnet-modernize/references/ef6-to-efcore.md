# Entity Framework 6 to EF Core

EF6 (6.3 and later) runs on .NET, so the data-access move is a separate, later wave, never bundled with the framework
hop. Port first with EF6; move to EF Core when there is a reason.

Differences to test before switching, each with characterisation tests on real (masked) data:
- Query translation: some LINQ queries translate differently or evaluate on the client; compare the SQL and results.
- Lazy loading is off unless configured; navigation properties that "just worked" may come back empty.
- Cascade delete and required relationships follow different conventions.
- Migrations history is not shared: start EF Core's history from the current schema.

Run old and new data access side by side on the same inputs (`modernize-parity`) before the switch.
