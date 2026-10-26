# Build: Maven or Gradle

- Pin the build plugin and every recipe module at exact versions in the plan; the recipe commit's trailer names them.
- Licences: OpenRewrite's core is Apache 2.0; some recipe modules are published under Moderne's source-available or
  proprietary licences. Each module's licence is checked and approved before use.
- Upgrade the build tool itself (wrapper, plugins) as its own step before the language or framework hop.
- Keep dependency versions in one place (a BOM or version catalogue) so recipes change them in one place.
