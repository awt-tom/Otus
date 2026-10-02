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
---

# idor — broken object/access-control (IDOR / BOLA) methodology

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the target is not confirmed in scope. Use only test accounts you control; prove access with a minimal non-destructive read — never modify/delete other users' data or mass-exfiltrate records.

## Goal (desired outcome)
Find endpoints where changing an object reference bypasses authorization (horizontal: another
user's data; vertical: higher-privilege actions) and prove it with a minimal, non-destructive PoC
backed by an authorization matrix.

## Steps
1. **Precondition / scope / inputs + accounts.** Confirm the target is in scope and gather
   object-referencing endpoints (`/users/123`, `?id=`, `?file=`, UUIDs, hashids) from `httpx` →
   `katana` / `ffuf` / Burp. Provision **two test accounts / roles** (A low-priv, B other-user or
   admin) for the matrix. Anchor a timestamped run directory to the repo root (never under
   `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_idor="${OTUS_RUN_DIR:-$ROOT/out/idor/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_idor"
   mkdir -p "$RUN/notes"
   echo "target confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/objects.md"; : > "$RUN/notes/authz-matrix.md"; : > "$RUN/findings.md"
   ```
2. **Enumerate object identifiers.** Map endpoints that take an object reference and capture the ID
   format (sequential / UUIDv4 / predictable hash) and ownership. Record them in `notes/objects.md`.
3. **Swap / escalate.** With account A's session, request account B's object IDs (**horizontal**);
   then attempt higher-privilege objects/actions and admin-only methods (**vertical**). Compare
   responses to the legitimate owner's; test method/param tampering (GET↔POST, role fields).
4. **Authorization matrix.** Build a `{account/role} × {object/action}` → allowed / denied / leaked
   grid in `notes/authz-matrix.md` so access gaps are explicit and reviewable.
5. **Confirm + impact PoC.** Confirm unauthorized access/modification with a **minimal** proof (read
   one other-user record, not mass dump; a single benign state change only if needed and reversible).
   Write each finding (endpoint, IDs, direction, impact) to `findings.md`.
6. **Marker + hand-off.** Always write a run marker, then feed confirmed findings to reporting:
   ```bash
   if grep -qiE '^\- ' "$RUN/findings.md"; then echo "idor: findings recorded" > "$RUN/summary.txt";
   else echo "no idor confirmed" > "$RUN/summary.txt"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
Mostly manual via Burp Suite — **Autorize** / **AuthMatrix** extensions automate the A-vs-B replay;
Repeater/Intruder for ID iteration; `ffuf` to enumerate ID ranges. No single CLI tool; the value is
the systematic authz matrix.

## Output formats
This skill writes `$RUN/notes/objects.md` (endpoints + ID formats), `$RUN/notes/authz-matrix.md`
(role×object grid), `$RUN/findings.md` (confirmed PoCs + impact), `$RUN/summary.txt` (run marker),
`$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "idor",
  "target": "<target_or_urls>",
  "run_dir": "out/idor/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "ids-enumerated":   { "attempted": true, "ok": true, "evidence": "notes/objects.md" },
    "authz-matrix":     { "attempted": true, "ok": true, "evidence": "notes/authz-matrix.md" },
    "confirmed-impact": { "attempted": true, "ok": true, "evidence": "findings.md" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (no second account, target unreachable,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Very high RAG value** — point at the HackTricks IDOR/BOLA and broken-access-control pages plus an
authz-testing checklist. Consumes object-referencing endpoints from `httpx` → `katana` / `ffuf` /
Burp; pairs with Burp Autorize/AuthMatrix; feeds reporting.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target confirmed in scope before any cross-account access attempt
    verify: judge
    evidence: notes/scope.txt
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
- **Two accounts make the test.** A finding is "A can reach B's object" — without a second
  identity you can only guess; `authz-matrix` needs real A-vs-B comparison.
- **Minimal, reversible proof only.** Read one other-user record; never mass-enumerate or
  delete/modify others' data; `confirmed-impact` fails hard (`on_fail: fail`), not auto-retried.
- Check vertical (privilege) and object-level (BOLA) access, not just sequential-ID swapping;
  UUIDs can still be IDOR if they leak elsewhere.
- A run that confirms nothing must still write `summary.txt` ("no idor confirmed") and `findings.md`
  so "ran but empty" ≠ "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/idor/<timestamp>/` (git-ignored).
