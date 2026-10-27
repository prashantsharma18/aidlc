<!-- aidlc-modernize template: cutover-checklist -->
# {{KEY}} · cutover · segment <name>

PRECONDITIONS  parity report approved <date, by> · rollback rehearsed incl. data <date> · stop criteria <link>
SEGMENT        <which traffic, users or records> · flag <name> · switched by <person>
STOP CRITERIA  | Signal | Threshold | Duration | Who decides | Action |
               |---|---|---|---|---|
REVERSE        new served, old shadowed: <mismatches outside accepted differences, must be 0> · outcome measure <name, baseline, now>
DATA           one writer writes both stores in one transaction: <where> · back-fill <idempotent, ranges done> ·
               reconciliation <queries, schedule> → <every query 0>
READERS        <reader — still fed? — evidence>
RESULT         <switched at, observed, rolled back? why>
NEXT SEGMENT   opened by <release approver> on <date>
