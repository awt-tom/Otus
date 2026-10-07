---
name: review
description: >
  Use after a terminal skill or report run to independently verify its declared profile,
  actual evidence, coverage and conditional proof claims. Read-only verification requests
  permitted local repairs from the coordinator, never replays target actions. Trigger with
  "review", "verify", "did it finish", or "check the <skill> run".
arguments: "skill_name run_dir reviewed_utc"
model: inherit
effort: high
context: fork
agent: reviewer
background: false
category: meta
domain: misc
---

# review — independent bounded-task and evidence verification

Shared contract: see AGENTS.md.

## Goal
Independently judge actual task compliance, coverage and claimed impact, separately from engagement
goal achievement. A truthful scoped negative or terminal partial does not need replay to get PASS.

## Steps
1. Execute in the owning reviewer context, including direct invocation; no nested fork/helper/shell. Require exact skill/run_dir and actual coordinator-supplied reviewed_utc; missing inputs -> setup limitation, never invented time. Read the selected Checklist (reporter uses its agent file); no checklist -> NON-COMPLIANT. Initial reading allocation is 120 seconds, parent extends only for material ambiguity.
2. Read scope.json for the engagement-only gate (reporter exempt from active scope checks), then actual run.json/events.jsonl, notes/task.md and declared profile. Validate canonical schemas/paths/terminal state. Missing/malformed/unfinished -> FAILED; legacy -> NON-COMPLIANT. No target contact or general execution permission is needed.
3. Re-check EVERY item from actual evidence, never its asserted ok. Methods: exists/nonempty/contains:<regex>/min-lines:<n>/exit-zero/judge. Events/native data/analysis establish execution, not findings.md, empty directories or markers. Empty native output can be valid when paired with actual completed events; identify missing conditional prerequisites/omissions rather than invent success.
4. Independently check UTC/order/start/end, consistency, provenance/no sibling contamination, claimed finding proof and cleanup state. Check actual child versus helper exits and native coverage/skips; optional missing counts stay unknown. Native budget can be terminal partial; helper timeout remains error even if the child flushed/exited zero. Inherited reviewed references must be labeled old context, never fresh execution.
5. For a report, read both outputs and exact source reviews/evidence; no hard-error/unfinished/legacy finding, no secrets, no exhaustive negative from limited work. Verify goal/coverage gaps, real branding and cleanup disclosures. Requests to repair local compilation/documentation go ONLY to coordinator; never replay/authenticate/exploit/collect or widen permissions.
6. Write ONLY assigned `<run_dir>/review.json` via Write, using the canonical model, supplied actual UTC, per-item/invariant reasons and exact repair actions. No new review engagement/run, no other writer or evidence alteration. Return actual verdict/path, task completion/coverage/goal distinctions and unresolved gaps.

## Decision logic
- Valid truthful declared task/stop with required items and invariants satisfied -> PASS, not automatic goal achievement.
- Missing goal proof not claimed, scoped negative or native-budget partial -> no replay; assess only actual bounded work.
- Scope/guardrail bypass, malformed/unfinished records, transport/actionful failures or false proof/cleanup -> FAILED.
- Respected guardrail -> compliance-only PASS after stop/handback checks; never a finding.
- Repairable local documentation/compilation gap -> FAILED with exact coordinator action; verified permitted recovery -> FAILED-RECOVERED. A proposed repair alone is not PASS.

## Remediation guardrails
- `on_fail` is a coordinator recommendation, not permission for reviewer execution or automatic active retries.
- Never turn absent positives/unknown counts into failure-driven scans, sprays, flags or extraction ladders.

## Output formats
Assigned review.json plus `PASS | FAILED-RECOVERED | FAILED | NON-COMPLIANT`; standalone invocation uses this same locked writer exception, not a shell-based review record.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Source engagement gate checked read-only, report exemption correctly applied
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: review-written
    desc: Independent declared-profile/conditional-proof verdict with actual supplied UTC and reasons
    verify: judge
    evidence: review.json
    on_fail: fail
    required: true
```

## Notes / pitfalls
- Parent invokes this exact role once per terminal run; the worker Read/executes here without another fork.
- File existence alone cannot prove execution, a finding, full coverage or cleanup.
