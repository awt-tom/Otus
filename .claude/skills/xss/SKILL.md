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
context: fork
agent: vuln-hunter
background: false
category: web
domain: web
---

# xss — cross-site scripting testing methodology

Shared contract: see AGENTS.md.

## Goal
Find and confirm XSS (reflected / stored / DOM) on an in-scope target by matching payloads to the
exact output context, then produce a minimal, non-destructive proof-of-concept and impact note.

## Steps
1. Select <=3 relevant sinks, not every input. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill xss --profile selected-sinks --coverage-set 'At most three candidate sinks')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; batches use `--targets-file "$HOSTS"`; nonzero STOP. Write notes/task.md with hypothesis, version/inputs and a 120-second initial task allocation.
2. Trace selected values into HTML/attribute/JS/URL/CSS context; for DOM XSS establish source-to-sink flow. Record actual contexts/untested cases in notes/contexts.md; reflection alone is not execution.
3. Choose a benign context-specific probe from verified documentation/RAG. No whole-input spray or automatic payload ladder. All CLI discovery/verification uses `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 120 -- <verified bounded argv>`; batch commands check the complete HOSTS list and fit the remaining task allocation.
4. Save actual responses and browser/Burp exports, with marker events for manual actions. Confirm only benign execution, never cookie theft/defacement. Record execution proof or explicit no-confirmation/GUI limitation in evidence/verification.md, referencing actual files; a marker or reflection cannot substitute for browser proof. Any callback requires its own endpoint gate.
5. Completed selected tests -> complete/completed; missing browser, native budget or inconclusive case -> partial, no false negative or replay. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other sinks and payload families' --item 'scope-confirmed=ok:../../scope.json' --item 'contexts-analysed=ok:notes/contexts.md' --item 'tested=ok:events.jsonl' --item 'confirmed-poc=ok:evidence/verification.md'`; claim only evidenced items/findings and actual state/cleanup. Return to the coordinator.

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
    desc: Events plus actual requests/exports substantiate the selected tests or disclosed omissions
    verify: judge
    evidence: events.jsonl
    on_fail: redo-skill
    required: true
  - id: confirmed-poc
    desc: Each confirmed XSS has a minimal, non-destructive PoC + impact (or documented "none")
    verify: judge
    evidence: evidence/verification.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Context is everything** — the same payload that fires in an HTML body is inert in a JS string or attribute; analyse the sink before picking a payload.
- **Benign PoC only.** `alert(document.domain)` / authorized callback — never steal real users' cookies, deface, or auto-exfiltrate; `confirmed-poc` fails hard (`on_fail: fail`).
- DOM XSS needs source→sink tracing in the browser/Burp DOM Invader, not just server reflection. Keep payloads in RAG, not inline, so they stay current.
- No proof is required for a truthful scoped negative; every claimed execution requires real evidence.
