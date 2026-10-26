# javax.* to jakarta.*

Jakarta EE 9 renamed the `javax.*` enterprise packages to `jakarta.*` (servlet, persistence, validation, annotation and
others). Spring Boot 3 and later need the Jakarta names.

- Run the approved OpenRewrite Jakarta migration recipe as one recipe commit: it renames imports, XML descriptors and
  service files consistently.
- Every library on the classpath must have a Jakarta version; a library still on `javax.*` blocks the hop and is a
  decision (upgrade, replace or wait).
- `javax.*` packages that are part of the JDK itself (for example `javax.crypto`, `javax.sql`) do not change.
