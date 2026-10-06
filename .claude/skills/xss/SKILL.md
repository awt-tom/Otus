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
1. Gather candidate inputs. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill xss)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; for batches use `--targets-file "$HOSTS"`. Nonzero STOP; check each new endpoint before testing.
2. **Context analysis (per input).** For each reflected/stored value, identify the **output context** — HTML body, tag attribute, JS string/template, URL, or CSS — since the context dictates the breakout. Record each sink + context in `notes/contexts.md`.
3. **Payload per sink (RAG-driven).** Pull context-appropriate payloads from the shared RAG (PayloadsAllTheThings/XSS + HackTricks); do **not** hardcode a payload library here. Start with a harmless reflection probe, then the context-specific breakout.
4. **Discovery:** all dalfox/verification commands use `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" -- <original argv>` (single endpoint: `--target "$TARGET"`). Save browser/Burp evidence and `event --event marker` entries for manual steps.
5. Confirm only benign execution (`alert(document.domain)` or an authorized callback), never cookie theft/defacement. Save context/payload/impact proof to `evidence/`. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'contexts-analysed=ok:notes/contexts.md' --item 'tested=ok:findings.md' --item 'confirmed-poc=ok:findings.md'`; add verified `--finding` entries and actual cleanup fields, or summary `no xss confirmed`.

## Modern tooling & alternatives
`dalfox` is the current standard for XSS discovery/verification; Burp Suite (Repeater/Intruder, DOM
Invader) for manual reflected/stored/DOM work. Legacy `XSStrike` is largely superseded.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and every endpoint/callback checked
    verify: judge
    evidence: ../../scope.json
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
- No XSS still finishes with that summary; findings.md is generated.
