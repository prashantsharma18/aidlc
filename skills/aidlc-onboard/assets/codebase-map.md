<!-- aidlc template: codebase-map -->
# {{NAME}}: codebase map
Owner: {{OWNER}} · Last verified: {{DATE}}, against commit <sha>
Read this before planning a change. Paths are from the repository root.

## What this service does
<purpose, who calls it, what it calls>

## Areas
<area path>   <responsibility>; may depend on <...>; owner <...>

## Key flows
<entry> -> <file> -> <file>   <the invariant that must hold>

## Where common changes go
- <kind of change>: <place>. Pattern: <exemplar>

## Shared capabilities (reuse; do not duplicate)
<capability>  <path>  <how it behaves on failure>

## Traps
- <fragile, generated, frozen or surprising area, and why>

## Tests
<how tests are organised; what needs real dependencies>
