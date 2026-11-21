<!-- aidlc template: intent -->
# {{KEY}} · {{TITLE}} · intent

## For the reviewer
- **Asked of:** The product owner, to accept or decline the work, set its priority and agree the provisional tier with whoever owns the risk; this is part of Ready, which the product owner decides with the spec (ADR 0026)
- **Record it:** In the tracker (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

```text
Kind      <new feature | defect | incident follow-up>   (a change to an approved spec is an amendment, not new intent)
Problem   <what is wrong, for whom, why now; link the evidence (support reports, incidents)>
Outcome   <the observable change, not an implementation>
Not now   <what is deliberately out>
Owner     <product owner>. Consulted: <security, domain>. Provisional tier: <1|2|3>
          (dials: risk <low|med|high>, complexity <..>, scope <..>; when uncertain, go up a tier)
```

Gate: an owner and a priority are set, the outcome is accepted, and the statement names no implementation.
