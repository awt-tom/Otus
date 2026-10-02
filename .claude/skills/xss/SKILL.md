---
name: xss
description: >
  Use when testing for cross-site scripting — reflected, stored, or DOM XSS — on an
  authorized web target. A testing methodology (context analysis → payload per sink →
  confirm → impact PoC) that invokes dalfox and Burp and pulls payloads from RAG. Not
  for SQL injection (use sqlmap) or content discovery (use ffuf).
arguments: "target_or_urls [param]"
model: inherit
effort: medium
context: inline
agent:
---

# xss — cross-site scripting testing methodology

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the target is not confirmed in scope. Use only benign, non-destructive proof-of-concept payloads — never weaponised payloads against real users.

## Goal (desired outcome)
Find and confirm XSS (reflected / stored / DOM) on an in-scope target by matching payloads to the
exact output context, then produce a minimal, non-destructive proof-of-concept and impact note —
not raw scanner output.

## Steps
1. **Precondition / scope / inputs.** Confirm the target is in scope and gather candidate
   injection points (parameters, forms, headers, DOM sinks) — usually URLs/params from `httpx` →
   `katana` / `ffuf` / Burp. Anchor a timestamped run directory to the repo root (never write
   under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/xss/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   echo "target confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/contexts.md"; : > "$RUN/findings.md"
   ```
2. **Context analysis (per input).** For each reflected/stored value, identify the **output
   context** — HTML body, tag attribute, JS string/template, URL, or CSS — since the context
   dictates the breakout. Record each sink + context in `notes/contexts.md`.
3. **Payload per sink (RAG-driven).** Pull context-appropriate payloads from the shared RAG
   (PayloadsAllTheThings/XSS + HackTricks XSS) — do **not** hardcode a payload library in this
   body. Start with a harmless reflection probe, then the context-specific breakout.
4. **Automated discovery & verification.** Run the `dalfox` tool skill over the candidate URL/param
   list to discover and verify reflected/DOM XSS at scale; use Burp Repeater for stored/DOM cases
   and anything dalfox can't reach. Log tool output under `$RUN/`.
5. **Confirm + impact PoC.** Confirm execution with a **benign** PoC (e.g. `alert(document.domain)`
   or a callback to your own authorized collaborator) — never cookie theft/defacement against real
   users. Write each confirmed finding (sink, context, payload, impact) to `findings.md`.
6. **Marker + hand-off.** Always write a run marker, then feed confirmed findings to reporting:
   ```bash
   if grep -qiE '^\- ' "$RUN/findings.md"; then echo "xss: findings recorded" > "$RUN/summary.txt";
   else echo "no xss confirmed" > "$RUN/summary.txt"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
`dalfox` is the current standard for XSS discovery/verification; Burp Suite (Repeater/Intruder,
DOM Invader) for manual reflected/stored/DOM work. Legacy `XSStrike` is largely superseded.

## Output formats
`dalfox` emits txt/json; this skill writes `$RUN/notes/contexts.md` (sinks + contexts),
`$RUN/findings.md` (confirmed PoCs + impact), `$RUN/summary.txt` (run marker), `$RUN/run.log`, and
a run record `$RUN/_run.json`:
```json
{
  "skill": "xss",
  "target": "<target_or_urls>",
  "run_dir": "out/xss/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "contexts-analysed":{ "attempted": true, "ok": true, "evidence": "notes/contexts.md" },
    "tested":           { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "confirmed-poc":    { "attempted": true, "ok": true, "evidence": "findings.md" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (target unreachable, out of scope) set
`status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Very high RAG value** — point at PayloadsAllTheThings/XSS and the HackTricks XSS page so payload
libraries live in the RAG store, not this body. Consumes candidate params/URLs from `httpx` →
`katana` / `ffuf` / Burp; invokes the `dalfox` tool skill; hands confirmed findings to reporting.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target confirmed in scope before any payload is sent
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: contexts-analysed
    desc: Injection points enumerated and their output contexts identified
    verify: nonempty
    evidence: notes/contexts.md
    on_fail: redo-part
    required: true
  - id: tested
    desc: XSS testing executed (dalfox/manual); run marker written (even if nothing confirmed)
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: confirmed-poc
    desc: Each confirmed XSS has a minimal, non-destructive PoC + impact (or documented "none")
    verify: judge
    evidence: findings.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Context is everything** — the same payload that fires in an HTML body is inert in a JS string
  or attribute; analyse the sink before picking a payload.
- **Benign PoC only.** `alert(document.domain)` / authorized callback — never steal real users'
  cookies, deface, or auto-exfiltrate; `confirmed-poc` fails hard (`on_fail: fail`), not retried.
- DOM XSS needs source→sink tracing in the browser/Burp DOM Invader, not just server reflection.
- Keep payloads in RAG (PayloadsAllTheThings/HackTricks), not inline, so they stay current.
- A run that confirms nothing must still write `summary.txt` ("no xss confirmed") and `findings.md`
  so "ran but empty" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/xss/<timestamp>/` (git-ignored).
