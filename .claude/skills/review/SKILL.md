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

## Inputs
- `skill_name` — skill that ran (e.g. `nuclei`); `run_dir` — its timestamped run dir (checklist `evidence` paths resolve relative to it).
- `max_part_retries` (default 2), `max_skill_retries` (default 1).

## Steps
1. **Load the contract.** Read `.claude/skills/<skill_name>/SKILL.md` and parse its `## Checklist` YAML. No checklist → stop: NON-COMPLIANT (unverifiable); report to the user.
2. **Load context.** Read `<run_dir>/run.json` — **mandatory on any terminal run**; missing/unparseable while evidence exists → FAIL. If `status: error`: a **platform-guardrail** block (per AGENTS.md) PASSes only if the run *respected* it (stopped, wrote `findings.md` handback, no retry/reword/split/bypass) — a bypass attempt → FAIL; any **other hard error** (tool-missing, network, auth, out-of-scope) → FAIL, no retries.
3. **Verify every item independently** against its `evidence` (path relative to `<run_dir>`) using its `verify` method (`exists`/`nonempty`/`contains:<regex>`/`min-lines:<n>`/`exit-zero`; `judge` by reading + assessing vs `desc`). **Do not trust `run.json` item `ok` — re-check.** Record pass/fail + reason per item.
4. **Check cross-cutting invariants** (read-only): timestamps parse ISO-8601 UTC with `finished >= started`; `run.json`/`findings.md` don't contradict evidence or `notes/*.txt`; every `evidence` file belongs to THIS run (no sibling contamination); a state-changing run has `loot/cleanup_verify.txt` with positive absence evidence (or states owed cleanup). Any violation → FAIL.
5. **Decide** (below), **remediate**, then **re-verify** affected items until PASS or budget exhausted. **Report** to `<run_dir>/review.md` (per-item table + invariants + verdict + what was redone); on FAIL, also surface a plain-language user message.

## Decision logic
Let `F` = required items that failed.
- Missing/unparseable `run.json`, a bypassed guardrail, or any invariant violation → **FAIL** (not retryable).
- `F` empty and invariants hold → **PASS.**
- Any `F` item is `on_fail: fail` (e.g. scope gate) → **FAIL immediately**, no retry.
- `run.json.status == error` (hard error / respected guardrail) → **FAIL**, not retryable here.
- All `F` are isolated evidence-producing steps and `part_retries < max_part_retries` → **REDO-PART** (re-run only those steps), `part_retries++`, re-verify.
- Else if `skill_retries < max_skill_retries` → **REDO-SKILL** (re-run the whole skill fresh), `skill_retries++`, re-verify.
- Else → **FAIL** (retries exhausted).

## Remediation guardrails
- **Never retry an `on_fail: fail` item** (scope/ambiguity/destructive = stop).
- **Never repeat a destructive/irreversible action** (exploit firing, data mod, lockout-risk spraying) on retry — if that's the only fix, FAIL and ask. Only an **operational** failure (no target action occurred) is safely re-runnable; an **actionful** failure is never replayed.
- Bounded by the retry budgets; a redo targets the **specific failed items**, not clean steps.

## Output formats
`<run_dir>/review.md` (verdict + per-item table + actions) and a verdict token: `PASS | FAILED-RECOVERED | FAILED | NON-COMPLIANT`.

## Notes / pitfalls
- Fork a **fresh** agent (`context: fork`) so the reviewer grades artifacts cold.
- Evidence that exists but is empty/garbage is a **FAIL** for that item — `nonempty`/`contains:` catch what bare `exists` waves through.
- Report *why* each item failed (missing vs empty vs pattern-miss), not just that it did.
