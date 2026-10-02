# Skill Review Guide — Checklist Spec + `review` Skill

> **Companion to** `skill-generator-guide.md`. This adds a verification layer:
> 1. A **`## Checklist` block** every skill carries — it declares each required part *and how to verify it from evidence*.
> 2. A **run record** the executing agent writes as it works.
> 3. A **separate `review` skill** that independently re-checks the evidence and then **redoes the missing part**, **redoes the whole skill**, or **tells the user it failed** — with bounded retries so it can't loop forever.
>
> **Core principle:** the reviewer never trusts "I did it." It verifies against artifacts on disk. A step counts as done only when its evidence proves it. This is why the reviewer is a *separate* skill, ideally forked into a fresh agent that didn't produce the work.

---

## 1. How the two layers fit together

```
┌─────────────┐   runs tool, writes      ┌──────────────────┐
│  task skill │ ───── evidence + ──────▶ │  out/<skill>/    │
│ (e.g. nmap) │       _run.json          │   scans/…        │
└─────────────┘                          │   _run.json      │
       ▲                                 └────────┬─────────┘
       │ redo-part / redo-skill                   │ reads (independently)
       │                                          ▼
       │                                 ┌──────────────────┐
       └──────────── verdict ─────────── │   review skill   │ ──▶ out/<skill>/_review.md
                                         │ verify → decide  │ ──▶ user (on FAIL)
                                         └──────────────────┘
```

- The **task skill** does the work and, for each checklist item, records what it attempted + where the evidence is.
- The **review skill** loads the task skill's checklist definition + the run record, **re-verifies every required item against the actual files**, decides a verdict, and drives remediation.

---

## 2. Layer 1 — the `## Checklist` block (goes in every skill)

Add this section to the body template in §3 of the reference. Declare it as a fenced YAML block so the reviewer can parse it deterministically.

```yaml
# ## Checklist   (place near the end of each SKILL.md body)
checklist:
  - id: scope-confirmed            # stable, unique within the skill
    desc: Target confirmed in scope before any active step
    verify: judge                  # how the reviewer checks it (see table)
    evidence: notes/scope.txt      # path (relative to the run dir) that proves it
    on_fail: fail                  # what to do if it fails (see table)
    required: true
  - id: allports-scan
    desc: Full TCP port sweep completed and saved
    verify: nonempty
    evidence: scans/allports.nmap
    on_fail: redo-part
    required: true
  - id: service-detail
    desc: Version/script scan run against discovered open ports
    verify: contains:open
    evidence: scans/detail.nmap
    on_fail: redo-part
    required: true
  - id: handoff-written
    desc: Open services summarized for downstream skills
    verify: nonempty
    evidence: out/nmap/summary.txt
    on_fail: redo-part
    required: false
```

**`verify` methods** (the reviewer runs these read-only against evidence):

| method | passes when | use for |
|---|---|---|
| `exists` | path exists | a file/dir was produced |
| `nonempty` | exists **and** has content (size/lines > 0) | output that must not be empty |
| `contains:<regex>` | file matches the regex | proof the step produced *real* results (e.g. `open`, `\[critical\]`) |
| `min-lines:<n>` | file has ≥ n lines | lists (subdomains, live hosts) |
| `exit-zero` | the step's recorded exit code is 0 | tool must have run cleanly |
| `judge` | reviewer reads evidence and assesses vs `desc` | things no pattern captures (scope, triage quality) |

**`on_fail` actions** (default remediation route for that item):

| action | meaning |
|---|---|
| `redo-part` | re-run only the step(s) that produce this evidence, then re-verify |
| `redo-skill` | the failure implies bad inputs/early breakage — re-run the whole skill |
| `fail` | **do not retry** — stop and escalate to the user (scope gates, destructive, ambiguous) |

**`required`**: `true` items block a PASS; `false` items are reported but don't fail the review.

**Authoring rules**
- Every checklist item must point at **evidence the step actually writes**. If a step produces nothing checkable, make it write a marker file (e.g. `echo "no findings" > nuclei.txt`) so "ran but found nothing" is distinguishable from "didn't run."
- The **scope gate is always `on_fail: fail`** — never retry your way past an unconfirmed target.
- Prefer `contains:`/`min-lines:` over bare `exists` where you can, so an empty/garbage file doesn't pass.
- Keep it to the *parts that matter*. 4–8 items per skill is typical.

---

## 3. Layer 2 — the run record (written by the task skill)

As the executing agent works through a skill, it writes `out/<skill>/_run.json`. This captures intent + any errors; the reviewer uses it for context (especially hard errors) but **re-verifies evidence itself**.

```json
{
  "skill": "nmap",
  "target": "10.10.11.23",
  "run_dir": "out/nmap",
  "started": "2026-10-01T21:05:00+02:00",
  "finished": "2026-10-01T21:12:40+02:00",
  "status": "complete",
  "items": {
    "scope-confirmed": { "attempted": true, "ok": true,  "evidence": "notes/scope.txt" },
    "allports-scan":   { "attempted": true, "ok": true,  "evidence": "scans/allports.nmap", "exit": 0 },
    "service-detail":  { "attempted": true, "ok": true,  "evidence": "scans/detail.nmap",   "exit": 0 },
    "handoff-written": { "attempted": true, "ok": true,  "evidence": "out/nmap/summary.txt" }
  },
  "errors": []
}
```

`status` ∈ `complete | partial | error`. On a hard failure (tool missing, network blocked, auth rejected, out of scope) set `status: error` and push a human-readable line to `errors[]` — this lets the reviewer **fail fast instead of retrying** something that can't succeed.

`started` and `finished` are **ISO-8601 UTC** timestamps (e.g. `2026-10-01T19:12:40Z`) and `finished` must be **>= `started`** — a well-formed, non-negative run window. Capture both from the **same clock** (`date -u +%Y-%m-%dT%H:%M:%SZ` at the start of the run and again immediately before writing `_run.json`). The reviewer may treat a malformed or inverted timestamp pair as a bad run record.

**Run-record invariant:** `_run.json` MUST be written on **every** terminal outcome — success, partial, or error — before handback. A run that produced evidence but no parseable `_run.json` is itself a defect, and the reviewer FAILS it.

### Error-handback `summary.txt` (required for any `status: error` run)
When a run ends in `status: error` (hard error **or** a platform-guardrail block), `summary.txt` is the user's single handback. It MUST contain, in order:
1. **STATUS** — one line: `STATUS: error — <reason>` (e.g. `blocked by platform guardrail (permission-classifier)`; `nmap not installed`).
2. **Completed before stop** — what finished and where that evidence is.
3. **Target state** — `changed` or `unchanged`. If changed, the mandatory **cleanup-state** field: what was created (DB rows, planted files, users/cron/implants) and whether it was **removed** (point to `loot/cleanup_verify.txt`) or is **STILL OWED**.
4. **Resolution options** — the concrete, user-driven next steps (for a guardrail: switch Claude Code to manual/default permission mode and/or enroll in Anthropic's Cyber Verification Program; for a hard error: install the tool / fix auth / re-run after X).

For a **platform-guardrail** stop, `summary.txt` also states explicitly that the run **respected the block** and attempted no retry/reword/split/background/bypass. The `privesc-root` blocked-run summary is the model for this shape.

---

## 4. The `review` skill (ready to drop in)

Create `.claude/skills/review/SKILL.md`:

```markdown
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
- `skill_name` — the skill that was run.
- `run_dir` — where its evidence lives (e.g. `out/nmap`).
- `max_part_retries` (default 2), `max_skill_retries` (default 1).

## Steps
1. **Load the contract.** `Read` the task skill's `SKILL.md` and parse its `## Checklist`
   YAML. If it has **no checklist**, stop: status = NON-COMPLIANT (cannot be verified).
   Report to the user and do not pass it.
2. **Load context.** Read `<run_dir>/_run.json`. **A parseable `_run.json` is mandatory on any
   terminal run** — if evidence exists but `_run.json` is missing or unparseable, go to FAIL
   (run-record invariant). If `status: error`:
   - **platform guardrail** (`errors[]` block type `guardrail:permission-classifier` /
     `guardrail:api-cyber-safeguard`): verify the run **respected the block** — stopped cleanly,
     wrote `summary.txt` in the error-handback shape, and did NOT retry / reword / split / background /
     bypass. PASS only if respected; a bypass attempt → FAIL.
   - **other hard error** (tool-not-found, network-blocked, auth-failed, out-of-scope): skip retries
     and go to FAIL with that reason.
3. **Verify every item independently** using its `verify` method against `evidence`
   (`exists`/`nonempty`/`contains:`/`min-lines:`/`exit-zero` via read-only checks;
   `judge` by reading the evidence and assessing against `desc`). Record pass/fail per item
   with the reason. **Do not trust `_run.json.ok`** — re-check.
3b. **Check cross-cutting invariants** (read-only, independent of the checklist):
   - **Timestamp sanity:** `started`/`finished` parse as ISO-8601 UTC and `finished >= started`.
   - **Self-report consistency:** `_run.json`/`summary.txt` narrative does not contradict the
     evidence or `notes/*.txt` (e.g. a claimed `--resolve` vs a logged Host header).
   - **Cross-run contamination:** every `evidence` file belongs to THIS `<run_dir>`, not a sibling
     concurrent run.
   - **Cleanup state:** a run that changed target state has `loot/cleanup_verify.txt` with positive
     absence evidence; an aborted mid-change run states the owed cleanup in `summary.txt`.
   Any invariant violation → FAIL.
4. **Decide** (see Decision logic). 
5. **Remediate** per the verdict, then **re-verify** the affected items (back to step 3)
   until PASS or a retry budget is exhausted.
6. **Write the report** to `<run_dir>/_review.md` (table of items → pass/fail/reason +
   final verdict + what was redone). On FAIL, also surface a plain-language message to the
   user.

## Decision logic
Let `F` = required items that failed verification.

- Missing/unparseable `_run.json` on a terminal run → **FAIL.** (run-record invariant; not retryable)
- Platform-guardrail error where the run tried to bypass the block (retry/reword/split/background) →
  **FAIL.** Not retryable — respecting the block is the only correct outcome.
- Any cross-cutting invariant violation (timestamp sanity, self-report consistency, cross-run
  contamination, cleanup state) → **FAIL.** Not retryable here.
- `F` empty (and invariants hold) → **PASS.** Write report, done.
- Any item in `F` has `on_fail: fail` (e.g. scope gate) → **FAIL immediately.** Do not retry.
- Else if `_run.json.status == error` (hard error, or a respected guardrail block) → **FAIL.** Not
  retryable here. (A respected guardrail block is reported as a clean, user-actionable FAIL.)
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
- If evidence exists but is empty/garbage, that's a FAIL for that item — `nonempty`/`contains:`
  catch this; don't let bare `exists` wave it through.
- Report *why* each item failed (missing file vs empty vs pattern-miss), not just that it did.
```

---

## 5. Verdicts the user will see

| Verdict | Meaning | What happens |
|---|---|---|
| `PASS` | All required items verified | `_review.md` written; proceed |
| `FAILED-RECOVERED` | Some items failed but a bounded redo fixed them | report notes what was redone; proceed |
| `FAILED` | Unrecoverable or retries exhausted | user is told which parts, what was tried, the cause, and the decision needed |
| `NON-COMPLIANT` | Target skill has no `## Checklist` | can't be verified → treated as fail; add a checklist |

---

## 6. Worked examples

### 6.1 `nmap` — a recoverable miss
Checklist from §2. Suppose the detail scan file is empty (tool ran but was interrupted):

- `scope-confirmed` → `judge` on `notes/scope.txt` → **pass**
- `allports-scan` → `nonempty scans/allports.nmap` → **pass**
- `service-detail` → `contains:open scans/detail.nmap` → **FAIL** (file empty, no match), `on_fail: redo-part`
- `handoff-written` → `nonempty` → fail but `required: false`

Decision: one isolated required failure, `on_fail: redo-part`, retries available → **REDO-PART**: re-run the service/version scan step only → re-verify → now contains `open` → **FAILED-RECOVERED**. Report lists the redo.

### 6.2 `nuclei` — distinguishing "no findings" from "didn't run"
Checklist excerpt:

```yaml
checklist:
  - id: templates-updated
    desc: nuclei-templates updated before scan
    verify: exit-zero
    evidence: _run.json#templates-updated
    on_fail: redo-part
    required: true
  - id: scan-ran
    desc: Scan executed against the live-host list
    verify: exists
    evidence: out/nuclei/nuclei.txt       # body writes "no findings" marker if empty
    on_fail: redo-skill
    required: true
  - id: triaged
    desc: Findings manually verified / false-positives dropped
    verify: judge
    evidence: out/nuclei/triage.md
    on_fail: fail                          # needs human/analyst judgement, don't auto-retry
    required: true
```

- If `nuclei.txt` is missing entirely → `scan-ran` fails with `redo-skill` (the scan never happened) → re-run whole skill.
- If `nuclei.txt` says "no findings" → `exists` **passes** (correctly: it ran, found nothing). This is why the body must write a marker.
- If `triage.md` is missing → `triaged` fails with `on_fail: fail` → **FAILED**, user told triage wasn't done (reviewer won't fake analyst judgement).

### 6.3 A hard failure (fail fast)
`_run.json.status == error`, `errors: ["subfinder: command not found"]`. Reviewer skips all retries → **FAILED**, message to user: the tool isn't installed, nothing to redo, install it or adjust the environment.

---

## 7. Runtime flow (how an orchestrator uses it)

```
run task skill  →  review(skill_name, run_dir)
                     ├─ PASS              → continue to next skill in the chain
                     ├─ FAILED-RECOVERED  → continue (note the redo in the run log)
                     ├─ FAILED            → stop the chain, surface message to user
                     └─ NON-COMPLIANT     → stop, tell user the skill needs a checklist
```

Chain example from the reference: after `subfinder → httpx → nuclei`, call `review nuclei out/nuclei` before trusting the findings; a `FAILED` there stops the pipeline instead of reporting bad results.

---

## 8. Template changes to make in the reference

1. **Body template (§3):** add the `## Checklist` YAML block near the end (spec in §2 above).
2. **Every task skill:** write `out/<skill>/_run.json` as it executes (§3 here), and make any "might produce nothing" step write a marker file so absence ≠ emptiness.
3. **Directory layout (§8 of reference):** add
   ```
   .claude/skills/review/SKILL.md
   out/<skill>/_run.json        # per-run record
   out/<skill>/_review.md       # per-run review report
   ```
4. **Build order (§9 of reference):** add the `review` skill right after the template is validated (step 1), so every subsequent skill is authored with its checklist from the start.