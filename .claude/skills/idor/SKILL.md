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
context: inline
agent:
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
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill idor)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Use two controlled test accounts/roles; account creation is a state change requiring recorded cleanup.
2. **Enumerate object identifiers.** Map endpoints that take an object reference (`/users/123`, `?id=`, `?file=`, UUIDs, hashids) from `httpx`→`katana`/`ffuf`/Burp; record ID format (sequential/UUIDv4/hash) and ownership in `notes/objects.md`.
3. **Swap / escalate.** With account A's session, request account B's object IDs (**horizontal**); then attempt higher-privilege objects/actions and admin-only methods (**vertical**). Test method/param tampering (GET↔POST, role fields); compare to the legitimate owner's response.
4. **Authorization matrix.** Build a `{account/role} × {object/action}` → allowed/denied/leaked grid in `notes/authz-matrix.md` so access gaps are explicit and reviewable.
5. CLI requests use `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" -- <original argv>`; manual requests save cases and marker events. Confirm one controlled record, not a mass dump. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'ids-enumerated=ok:notes/objects.md' --item 'authz-matrix=ok:notes/authz-matrix.md' --item 'confirmed-impact=ok:findings.md'`; add verified `--finding` entries referencing cases and actual cleanup fields, or summary `no idor confirmed`.

## Modern tooling & alternatives
Mostly manual via Burp Suite — **Autorize** / **AuthMatrix** automate the A-vs-B replay; Repeater/
Intruder for ID iteration; `ffuf` to enumerate ID ranges. No single CLI tool; the value is the
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
    desc: Object-referencing endpoints and their ID formats mapped
    verify: nonempty
    evidence: notes/objects.md
    on_fail: redo-part
    required: true
  - id: authz-matrix
    desc: Account/role x object/action authorization matrix built
    verify: nonempty
    evidence: notes/authz-matrix.md
    on_fail: redo-part
    required: true
  - id: confirmed-impact
    desc: Confirmed IDOR/BOLA has minimal non-destructive proof + impact (or documented "none")
    verify: judge
    evidence: findings.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Two accounts make the test.** A finding is "A can reach B's object" — without a second identity you can only guess; the authz matrix needs real A-vs-B comparison.
- **Minimal, reversible proof only.** Read one other-user record; never mass-enumerate or delete/modify others' data; `confirmed-impact` fails hard (`on_fail: fail`).
- Check vertical and object-level access, not just sequential IDs. No confirmed IDOR still finishes with that summary.
