<!-- aidlc template: readiness -->
# {{KEY}} · readiness

The worst of the five decides.

## For the reviewer
- **Asked of:** The release approver, to decide ship, limit or hold; the owning team confirms monitoring and rollback
- **Record it:** In change management; the owning team's confirmation in this record
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

## 1. Scope known
- [ ] Users: {{what people experience, including refusals}}
- [ ] Services and blast radius: {{services}}
- [ ] Success signal: {{signal}}

## 2. Evidence passing
- [ ] Required checks green and code-owner approval on every PR; specialist reviews recorded
- [ ] Staging behaviour confirmed: {{what was seen}}

## 3. Access limited
- [ ] Who may change the flag or configuration in production: {{who}}; no agent or pipeline identity can

## 4. Monitoring in place
- [ ] Monitoring checked against the `adding-observability` pre-launch list: alerts with thresholds, routed to {{on-call}}, each pointing to a runbook
- [ ] Dashboard: {{link}}

## 5. Recovery defined
- [ ] Rollback: {{fastest route}}, pre-approved for on-call, rehearsed in staging on {{YYYY-MM-DD}}
- [ ] Runbook: {{path}}

## Decision
{{ship, limit or hold}}. Release approver: {{name}}, {{YYYY-MM-DD}}
