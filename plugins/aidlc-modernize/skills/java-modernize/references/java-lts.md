# Java 8, 11 or 17 to a current LTS (21 or 25)

- Target an LTS: 21 or 25. Move through the build first (compiler release, toolchains, CI images), then the code.
- Removed or encapsulated in the hops: Java EE modules dropped from the JDK in 11 (JAXB, JAX-WS, CORBA: add them as
  dependencies or move to Jakarta), strong encapsulation of JDK internals in 17 (`--add-opens` is a decision, not a fix),
  the Security Manager deprecated for removal.
- Behaviour to pin before the hop: date and time formatting (CLDR locale data became the default in 9), string
  concatenation of floating-point values, default garbage collector and memory settings.
- OpenRewrite has migration recipes per version (for example "migrate to Java 21"); approve the exact recipe and version.
