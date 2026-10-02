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
---

# review — independent completion check & remediation

**Scope guard:** Verification is read-only. Re-running a skill inherits that skill's own
scope guard; never re-run anything whose target is not confirmed in scope.

## Goal
Decide, from evidence alone, whether `<skill_name>`'s run in `<run_dir>` completed every
required checklist item. If not, drive the right fix (redo part / redo skill) or stop and
tell the user — without ever looping indefinitely or repeating a destructive action.

## Inputs
- `skill_name` — the skill that was run (e.g. `port-scanner`, `nuclei`).
- `run_dir` — the timestamped run directory where its evidence lives
  (e.g. `out/port-scanner/20261001T230500`). Checklist `evidence` paths resolve relative to it.
- `max_part_retries` (default 2), `max_skill_retries` (default 1).

## Steps
1. **Load the contract.** `Read` the task skill's `SKILL.md` (`skills/<skill_name>/SKILL.md`) and
   parse its `## Checklist` YAML. If it has **no checklist**, stop: status = NON-COMPLIANT
   (cannot be verified). Report to the user and do not pass it.
2. **Load context.** Read `<run_dir>/_run.json` if present. If `status: error` with a hard
   error (tool-not-found, network-blocked, auth-failed, out-of-scope), skip retries and go
   to FAIL with that reason.
3. **Verify every item independently** using its `verify` method against `evidence`, resolving
   each path relative to `<run_dir>` (`exists` / `nonempty` / `contains:<regex>` / `min-lines:<n>`
   / `exit-zero` via read-only checks; `judge` by reading the evidence and assessing against
   `desc`). Record pass/fail per item with the reason. **Do not trust `_run.json.ok`** — re-check.
4. **Decide** (see Decision logic).
5. **Remediate** per the verdict, then **re-verify** the affected items (back to step 3)
   until PASS or a retry budget is exhausted.
6. **Write the report** to `<run_dir>/_review.md` (table of items → pass/fail/reason +
   final verdict + what was redone). On FAIL, also surface a plain-language message to the
   user.

## Decision logic
Let `F` = required items that failed verification.

- `F` empty → **PASS.** Write report, done.
- Any item in `F` has `on_fail: fail` (e.g. scope gate) → **FAIL immediately.** Do not retry.
- Else if `_run.json.status == error` (hard error) → **FAIL.** Not retryable here.
- Else if all of `F` are isolated, evidence-producing steps and `part_retries < max_part_retries`
  → **REDO-PART:** re-run only the steps that produce those evidences (by following the
  matching numbered steps in the task skill), `part_retries++`, re-verify.
- Else if `skill_retries < max_skill_retries` → **REDO-SKILL:** re-run the whole task skill
  from the top (fresh), `skill_retries++`, re-verify.
- Else → **FAIL.** Retries exhausted.

## Remediation rules (guardrails)
- **Never retry an `on_fail: fail` item.** Scope/ambiguity/destructive = stop.
- **Never repeat a destructive or irreversible action** on retry (exploit firing, data
  modification, account-lockout-risk spraying). If the only fix is such an action, FAIL and
  ask the user.
- **Bounded:** at most `max_part_retries` part-redos and `max_skill_retries` full-redos.
- A redo must target the **specific failed items**; don't re-run clean steps needlessly.

## Output formats
- `<run_dir>/_review.md` — human-readable verdict + per-item table + actions taken.
- Verdict token for programmatic use: `PASS | FAILED-RECOVERED | FAILED | NON-COMPLIANT`.
- On FAIL: a direct user message stating which parts failed, what was tried, the likely
  cause, and the decision needed from the user.

## RAG / cross-skill
- Reads the target skill's own `## Checklist` (the contract) and re-invokes that skill for
  redos. No external RAG required; it's a meta-skill over whatever skill it's pointed at.

## Notes / pitfalls
- Prefer forking into a fresh agent (`context: fork`) so the reviewer hasn't "seen" the work
  and grades the artifacts cold.
- If evidence exists but is empty/garbage, that's a FAIL for that item — `nonempty` / `contains:`
  catch this; don't let bare `exists` wave it through.
- Report *why* each item failed (missing file vs empty vs pattern-miss), not just that it did.
