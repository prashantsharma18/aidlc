<!-- aidlc template: adr -->
# {{NUMBER}} · {{TITLE}}

## For the reviewer
- **Asked of:** The tech lead or architect (the decider), to accept the decision with the design; consumers agree a contract change
- **Record it:** On the Status line (Accepted at design approval), and on the work item with the design's version and commit (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

Status: Proposed | Accepted at design approval ({{who approved, and how it was confirmed}}) | Superseded by {{n}}
Decider: {{name/role}} · Agreed: {{owners and consumers}} · Work item: {{key}} · Tier: {{n}}
Scope: {{one repository: it moves to that repository's docs/adr/ | several repositories: it stays in the home repository's docs/adr/, and each affected repository gets a one-line ADR that links it at a commit}} · Draft: `{{KEY}}-adr-{{n}}.md`

## Context
{{why a decision is needed}}

## Drivers
- {{checkable driver}}

## Options
A. {{option}} — {{chosen | rejected: reason}}

## Decision
- {{what is decided, specific enough to check}}

## Consequences
- {{consequence}} — enforced by {{check, test or code owner}} | advised by {{rules-file line}}
- Revisit if {{condition}}
