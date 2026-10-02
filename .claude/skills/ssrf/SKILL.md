---
name: ssrf
description: >
  Use when testing for server-side request forgery (SSRF) on an authorized web target —
  parameters that make the server fetch a URL, cloud metadata (169.254.169.254), internal
  services, filter bypasses. A testing methodology (param ID → internal targets → bypass →
  impact) using an OOB collaborator and RAG payloads. Not for client-side XSS (use xss).
arguments: "target_or_urls [param]"
model: inherit
effort: high
context: inline
agent:
---

# ssrf — server-side request forgery testing methodology

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the target is not confirmed in scope. Use only your own authorized OOB collaborator; demonstrate reach with a minimal PoC — never exfiltrate cloud credentials/secrets beyond proof or pivot destructively into internal services.

## Goal (desired outcome)
Identify server-side request forgery on an in-scope target, bypass any filtering, and prove impact
(internal service / cloud-metadata reachability) with a minimal, non-destructive proof-of-concept.

## Steps
1. **Precondition / scope / inputs + OOB.** Confirm the target is in scope and collect candidate
   parameters that cause the server to fetch a URL (webhooks, link/image/PDF fetchers, importers,
   open redirects, `url=`/`next=`/`dest=` style params) from `httpx` → `katana` / `ffuf` / Burp.
   Stand up an authorized OOB listener (Burp Collaborator / interactsh). Anchor a timestamped run
   directory to the repo root (never write under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_ssrf="${OTUS_RUN_DIR:-$ROOT/out/ssrf/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_ssrf"
   mkdir -p "$RUN/notes"
   echo "target confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/candidates.md"; : > "$RUN/findings.md"
   ```
2. **Parameter identification.** Enumerate the parameters/headers that trigger an outbound request;
   point each at your OOB host to confirm the server fetches attacker-controlled URLs. Record
   confirmed-fetching params in `notes/candidates.md`.
3. **Internal / metadata targets.** For confirmed SSRF, probe internal reachability — loopback
   (`127.0.0.1`, `localhost`), internal RFC1918 ranges, link-local **cloud metadata**
   (`169.254.169.254`, GCP/Azure/AWS IMDS paths) — to demonstrate reach only. Log attempts.
4. **Filter bypass (RAG-driven).** When blocked, apply documented bypasses — alternate IP encodings
   (decimal/octal/hex), DNS rebinding, redirect chains, `[::]`/IPv6, scheme/wrapper tricks — pulled
   from the shared RAG (PayloadsAllTheThings/SSRF + HackTricks SSRF). Do **not** hardcode a payload
   library here.
5. **Confirm + impact PoC.** Confirm via OOB callback or reflected response and demonstrate minimal
   impact (e.g. metadata endpoint reachable, internal service banner) — **do not** dump full cloud
   credentials or weaponise. Write each finding (param, payload, bypass, impact) to `findings.md`.
6. **Marker + hand-off.** Always write a run marker, then feed confirmed findings to reporting:
   ```bash
   if grep -qiE '^\- ' "$RUN/findings.md"; then echo "ssrf: findings recorded" > "$RUN/summary.txt";
   else echo "no ssrf confirmed" > "$RUN/summary.txt"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
Burp Suite (Repeater + Collaborator) is the manual hub; `interactsh` for standalone OOB; param
discovery via `ffuf`/`katana`/Param Miner. `nuclei` SSRF templates catch known patterns — this
skill covers the manual/bypass reasoning those miss.

## Output formats
This skill writes `$RUN/notes/candidates.md` (fetching params), `$RUN/findings.md` (confirmed PoCs
+ impact), `$RUN/summary.txt` (run marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "ssrf",
  "target": "<target_or_urls>",
  "run_dir": "out/ssrf/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":   { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "params-identified": { "attempted": true, "ok": true, "evidence": "notes/candidates.md" },
    "tested":            { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "confirmed-impact":  { "attempted": true, "ok": true, "evidence": "findings.md" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (target unreachable, out of scope) set
`status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Very high RAG value** — point at PayloadsAllTheThings/SSRF, the HackTricks SSRF page, and cloud
IMDS references so the bypass/payload library lives in RAG, not this body. Consumes candidate
params/URLs from `httpx` → `katana` / `ffuf` / Burp; uses an OOB collaborator; feeds reporting.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target confirmed in scope before any outbound-fetch attempt
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: params-identified
    desc: Parameters that trigger server-side outbound requests enumerated
    verify: nonempty
    evidence: notes/candidates.md
    on_fail: redo-part
    required: true
  - id: tested
    desc: SSRF testing executed (internal/metadata targets + bypasses); run marker written
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: confirmed-impact
    desc: Confirmed SSRF has OOB/response proof + minimal impact, no secret exfil (or documented "none")
    verify: judge
    evidence: findings.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Minimal proof only.** Show reach (callback, metadata endpoint, internal banner) — never dump
  full cloud credentials or pivot destructively; `confirmed-impact` fails hard (`on_fail: fail`).
- Blind SSRF needs an OOB collaborator — a filtered reflected response does not mean "not
  vulnerable"; check your listener.
- Keep bypass payloads in RAG (encodings, rebinding, redirects), not inline, so they stay current.
- A run that confirms nothing must still write `summary.txt` ("no ssrf confirmed") and `findings.md`
  so "ran but empty" ≠ "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/ssrf/<timestamp>/` (git-ignored).
