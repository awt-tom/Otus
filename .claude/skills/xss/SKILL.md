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
category: web
domain: web
---

# xss — cross-site scripting testing methodology

Shared contract: see AGENTS.md.

## Goal
Find and confirm XSS (reflected / stored / DOM) on an in-scope target by matching payloads to the
exact output context, then produce a minimal, non-destructive proof-of-concept and impact note.

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Gather candidate injection points (params, forms, headers, DOM sinks) from `httpx`→`katana`/`ffuf`/Burp.
2. **Context analysis (per input).** For each reflected/stored value, identify the **output context** — HTML body, tag attribute, JS string/template, URL, or CSS — since the context dictates the breakout. Record each sink + context in `notes/contexts.md`.
3. **Payload per sink (RAG-driven).** Pull context-appropriate payloads from the shared RAG (PayloadsAllTheThings/XSS + HackTricks); do **not** hardcode a payload library here. Start with a harmless reflection probe, then the context-specific breakout.
4. **Automated discovery & verification.** Run `dalfox` over the candidate URL/param list to discover/verify reflected/DOM XSS at scale; use Burp Repeater (DOM Invader) for stored/DOM cases dalfox can't reach. Log output under `$RUN/`.
5. **Confirm + impact PoC.** Confirm execution with a **benign** PoC (`alert(document.domain)` or a callback to your own authorized collaborator) — never cookie theft/defacement against real users. Write each finding (sink, context, payload, impact) to `findings.md`; if none, `no xss confirmed`. Write `run.json`.

## Modern tooling & alternatives
`dalfox` is the current standard for XSS discovery/verification; Burp Suite (Repeater/Intruder, DOM
Invader) for manual reflected/stored/DOM work. Legacy `XSStrike` is largely superseded.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
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
    evidence: findings.md
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
- **Context is everything** — the same payload that fires in an HTML body is inert in a JS string or attribute; analyse the sink before picking a payload.
- **Benign PoC only.** `alert(document.domain)` / authorized callback — never steal real users' cookies, deface, or auto-exfiltrate; `confirmed-poc` fails hard (`on_fail: fail`).
- DOM XSS needs source→sink tracing in the browser/Burp DOM Invader, not just server reflection. Keep payloads in RAG, not inline, so they stay current.
- A run that confirms nothing must still write `findings.md` ("no xss confirmed").
