# Spring Boot 2.x to 3.5 to 4.x

Go through 3.5, then 4.x: each hop is its own recipe commit and review.

- 2.x to 3.x: Java 17 or later, Jakarta names, Spring Security configuration changes, property renames (the
  properties migrator module reports them at start-up), observability moved to Micrometer.
- 3.5 to 4.x: Spring Boot 4.0 has been generally available since November 2025; Boot 3.5's open-source support ended
  on 30 June 2026. Boot 4 brings Jakarta EE 11 and Jackson 3, so JSON output (property order, null handling, date
  formats) can change: consumer contract tests and `modernize-parity` before release.
- Check the dates on Spring's support policy page when you plan; they move with each release.
