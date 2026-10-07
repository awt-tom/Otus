---
name: idor
description: >
  Use when testing for broken object/access control — IDOR / BOLA — on an authorized web
  target: endpoints that reference objects by ID (numeric, UUID, filename) where swapping
  the reference grants horizontal or vertical access. A methodology (enumerate IDs →
  swap/escalate → authz matrix). Also known as broken access control. Not for XSS/SSRF.
arguments: "target_or_urls [second_account]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: web
domain: web
---

# idor — broken object/access-control (IDOR / BOLA) methodology

Shared contract: see AGENTS.md.

## Goal
Find endpoints where changing an object reference bypasses authorization (horizontal: another user's
data; vertical: higher-privilege actions) and prove it with a minimal, non-destructive PoC backed by
an authorization matrix.

## Steps
1. Select <=3 object/action pairs and two existing controlled accounts/roles; initial task 120 seconds. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill idor --profile controlled-pairs --coverage-set 'At most three controlled object/action pairs')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, ownership, allocation and minimum proof. Missing second identity -> not-tested/partial, not a negative; no automatic account creation.
2. Reuse known endpoints/identifiers, record formats and actual A/B ownership in notes/objects.md. No mass ID enumeration, crawler or automatic method/role tampering ladder.
3. For each selected pair compare the owner's response with A requesting B's known controlled object, or one specifically justified role action. Use a read-only/minimal reversible case; no deletion/modification of others' data. Save actual cases and compare contents, not status codes alone.
4. Build notes/authz-matrix.md with identity/role, controlled object/action, expected/actual allowed-denied-leaked result, case refs and explicit untested/omitted pairs. Tokens stay only in private raw evidence.
5. CLI: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 120 -- <verified bounded request argv>`; shorter native timeouts fit the remaining allocation. Manual cases require real exports/marker events. Save proof or no-confirmation/limitations in evidence/verification.md. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected objects, roles and actions' --item 'scope-confirmed=ok:../../scope.json' --item 'ids-enumerated=ok:notes/objects.md' --item 'authz-matrix=ok:notes/authz-matrix.md' --item 'confirmed-impact=ok:evidence/verification.md'`; complete only finished pairs, otherwise partial/error with actual state/cleanup. Return to coordinator, no replay for missing goal proof.

## Modern tooling & alternatives
Mostly manual via Burp Suite — **Autorize** / **AuthMatrix** automate the A-vs-B replay; Repeater/
Intruder for selected controlled cases. No single CLI tool; the value is the
systematic authz matrix.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization, endpoint, and test-account use checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: ids-enumerated
    desc: Selected endpoints, formats and controlled ownership or missing prerequisite disclosed
    verify: judge
    evidence: notes/objects.md
    on_fail: redo-part
    required: true
  - id: authz-matrix
    desc: Actual A/B comparisons and raw cases support matrix; untested pairs explicitly marked
    verify: judge
    evidence: notes/authz-matrix.md
    on_fail: redo-part
    required: true
  - id: confirmed-impact
    desc: Confirmed IDOR/BOLA has minimal non-destructive proof + impact (or documented "none")
    verify: judge
    evidence: evidence/verification.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Two accounts make the test.** A finding is "A can reach B's object" — without a second identity you can only guess; the authz matrix needs real A-vs-B comparison.
- **Minimal, reversible proof only.** Read one other-user record; never mass-enumerate or delete/modify others' data; `confirmed-impact` fails hard (`on_fail: fail`).
- Check vertical and object-level access, not just sequential IDs. No confirmed IDOR still finishes with that summary.
