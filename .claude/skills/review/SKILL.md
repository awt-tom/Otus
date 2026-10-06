---
name: review
description: >
  Use after running any skill to verify it actually completed every required part.
  Independently re-checks each checklist item against the evidence on disk (not the
  executor's self-report), then redoes the missing part, redoes the whole skill, or
  reports failure to the user. Trigger with "review", "verify", "did it finish",
  "check the <skill> run".
arguments: "skill_name run_dir [max_part_retries] [max_skill_retries]"
model: inherit
effort: high
context: fork
agent: general-purpose
category: meta
domain: misc
---

# review — independent completion check & remediation

Shared contract: see AGENTS.md. Verification is **read-only**; a redo inherits the target skill's scope (never re-run an out-of-scope target).

## Goal
Decide, from evidence alone, whether `<skill_name>`'s run in `<run_dir>` completed every required
checklist item — then drive the right fix (redo part / redo skill) or stop and tell the user, without looping forever or repeating a destructive action.

## Steps
1. Standalone: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill review)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Load the reviewed skill Checklist (reporter uses its agent file); no checklist means NON-COMPLIANT. Inside the locked reviewer agent use its read-only gate/Write verdict procedure instead, not a helper invocation or a nested review run.
2. Read reviewed run.json/events.jsonl/scope.json and validate AGENTS.md schemas. Legacy, missing, malformed, or unfinished records are not promoted. Hard errors FAIL without retries; respected guardrail stops are the compliance-only exception in AGENTS.md, not confirmed findings.
3. **Verify every item independently** against its `evidence` (path relative to `<run_dir>`) using its `verify` method (`exists`/`nonempty`/`contains:<regex>`/`min-lines:<n>`/`exit-zero`; `judge` by reading + assessing vs `desc`). **Do not trust `run.json` item `ok` — re-check.** Record pass/fail + reason per item.
4. **Check cross-cutting invariants** (read-only): timestamps parse ISO-8601 UTC with `finished >= started`; `run.json`/`findings.md` don't contradict evidence or `notes/*.txt`; every `evidence` file belongs to THIS run (no sibling contamination); a state-changing run has `loot/cleanup_verify.txt` with positive absence evidence (or states owed cleanup). Any violation → FAIL.
5. Decide/re-verify within budget. Write ONLY assigned `<run_dir>/review.json` via Write as the reviewer-role exception in AGENTS.md; record actual UTC reviewed time. Standalone local checks use `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- <read-only argv>`; save a verdict summary to `notes/verdict.txt`, then `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'review-written=ok:notes/verdict.txt' --target-state unchanged --cleanup not-needed`. Never alter source evidence or hand-write run JSON/findings.

## Decision logic
Let `F` = required items that failed.
- Missing/unparseable/unfinished run records, bypassed guardrails, or invariant violations FAIL without retries.
- A respected guardrail PASSes compliance-only after the stop/handback invariants are checked; skip unfinished action items.
- `F` empty and invariants hold → **PASS.**
- Any `F` item is `on_fail: fail` (e.g. scope gate) → **FAIL immediately**, no retry.
- Other `run.json.status == error` outcomes FAIL, not retryable.
- All `F` are isolated evidence-producing steps and `part_retries < max_part_retries` → **REDO-PART** (re-run only those steps), `part_retries++`, re-verify.
- Else if `skill_retries < max_skill_retries` → **REDO-SKILL** (re-run the whole skill fresh), `skill_retries++`, re-verify.
- Else → **FAIL** (retries exhausted).

## Remediation guardrails
- **Never retry an `on_fail: fail` item** (scope/ambiguity/destructive = stop).
- **Never repeat a destructive/irreversible action** (exploit firing, data mod, lockout-risk spraying) on retry — if that's the only fix, FAIL and ask. Only an **operational** failure (no target action occurred) is safely re-runnable; an **actionful** failure is never replayed.
- Defaults: two part retries / one whole-skill retry; target only failed items in fresh helper runs.

## Output formats
Assigned `<run_dir>/review.json` per AGENTS.md and token `PASS | FAILED-RECOVERED | FAILED | NON-COMPLIANT`; standalone review work gets its own helper record. Recovered PASS requires actual independently verified recovery, not a REDO recommendation.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope exists and is valid; no target contact during verification
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: review-written
    desc: Independent per-item and invariant verdict recorded
    verify: nonempty
    evidence: notes/verdict.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- Fork a **fresh** agent (`context: fork`) so the reviewer grades artifacts cold.
- Evidence that exists but is empty/garbage is a **FAIL** for that item — `nonempty`/`contains:` catch what bare `exists` waves through.
