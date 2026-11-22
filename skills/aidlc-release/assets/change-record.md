<!-- aidlc template: change-record -->
# {{KEY}} · change record

## For the reviewer
- **Asked of:** The release approver, to approve the change and its stop criteria
- **Record it:** In change management (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

## Change
- **What:** {{what is switched or deployed}}
- **Artefact:** build of commit {{sha}}; digest recorded by the release pipeline
- **Tier:** {{n}}
- **Links:** {{work item; spec version; plan; pull requests with evidence and reviews; readiness}}

## Plan
1. {{staging step}}
2. {{rehearse rollback}}
3. {{production step}}
4. {{watch window}}

## Stop and caution
- **Stop:** {{signal, threshold, duration}} -> {{action at once, by whom, with no further approval}}
- **Caution:** {{signal}} -> hold the next stage; follow the runbook

## Roles
- **Agent:** read-only: summaries and proposals; no flags, configuration or credentials
- **Submitted by:** {{engineer}}, drafted with the agent
- **Approved by:** {{release approver}}, in change management, record {{change management record ID}} ({{how the AI confirmed it}})

## Follow-ups
- Flag removal: {{owner, date, work item}}
