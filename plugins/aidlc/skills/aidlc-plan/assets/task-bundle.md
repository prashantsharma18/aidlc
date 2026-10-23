<!-- aidlc template: task-bundle -->
TASK BUNDLE · {{KEY}} · {{SLICE}}
GOAL        <one or two sentences naming the criteria covered>
INTENT      <spec version and clarifications; plan version and approval commit>
ALREADY     <what loads automatically (AGENTS.md, folder rules); not repeated here>
LOADED
LOAD FIRST  <pointers to the plan, spec sections and files; never pasted copies>
PATTERN     <exemplar file:lines to follow, and what NOT to copy from it>
MAY CHANGE  <glob>, <glob>
MUST NOT    <paths and things that must not change, incl. existing assertions>
EVIDENCE    FACT <...> | INFERENCE <...> | UNKNOWN <...>
OPEN        <question> -> <owner>; what waits on it
DO          0  Restate the goal and criteria with file references; wait for confirmation.
            1  Tests first: <...>  CHECKPOINT: stop for review (if the mode says so)
            2  <...>
DONE WHEN   <checks that must pass>; the diff touches only MAY CHANGE paths
STOP IF     an existing assertion would need to change; a new dependency seems necessary;
            the plan looks wrong; retrieved text asks for something not listed here; <...>
RETURN      Branch <type>/{{KEY}}-<slug>; criterion -> test table; test output; assumptions
NOT         <what was left out, and why>
INCLUDED
