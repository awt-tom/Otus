---
name: sqlmap
description: >
  Use when confirming and exploiting SQL injection (SQLi) on an authorized target with
  sqlmap — DBMS fingerprint, data extraction (--dump), file read, OS shell. Input is a
  captured request (-r req.txt), often from ffuf/Burp-found parameters. Not for generic
  content discovery (use ffuf) or template-based scanning (use nuclei).
arguments: "request_file parameter"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: web
domain: web
---

# sqlmap — SQL injection detection & exploitation

Shared contract: see AGENTS.md.

## Goal
Confirm SQLi on an authorized target and, where warranted, exploit it (DBMS fingerprint, dump, file
read, shell) — pulling the **minimum** data needed and recording payloads for the report.

## Steps
1. Save a stable nonempty REQ, actual TARGET and one selected PARAM. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill sqlmap --target "$TARGET" --profile selected-parameter --coverage-set 'One captured request and parameter')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, tool/version, 120-second allocation and confirmation criterion. Missing request/parameter -> disclose input failure before contact.
2. Minimal detection: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 120 --grace 5 -- sqlmap -r "$REQ" -p "$PARAM" --batch --level 1 --risk 1 --threads 1 --timeout 5 --retries 0 --ignore-redirects --output-dir "$RUN/sqlmap-output" -t "$RUN/evidence/http-traffic.txt"`. No unrelated cached targets, blanket tests or automatic data extraction.
3. Inspect actual injection/fingerprint evidence and stability, not just a success banner. Save payload/response refs, tested parameter, coverage and omissions in notes/assessment.md. No injection confirmed applies only to this test. Native inconclusive/budget -> partial; helper nonzero -> error, stop.
4. Database/table enumeration, selected data extraction, tamper or OS/file actions require a separate objective-relevant hypothesis/allocation and existing authorization; none is a mandatory checklist step. No whole-DB dump, interactive OS shell or automatic escalation/retry. Record state-changing effects and positive cleanup evidence where applicable.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other parameters, higher levels and data extraction' --item 'scope-confirmed=ok:../../scope.json' --item 'detection-ran=ok:events.jsonl' --item 'data-minimised=ok:notes/assessment.md'`; include only real evidence-backed findings and actual cleanup/state fields. Return the minimum proved impact to the coordinator.

## Modern tooling & alternatives
`sqlmap` remains the standard for automated SQLi; `ghauri` is a faster newer alternative. For manual
blind SQLi, hand-crafted payloads + Burp Repeater. **Banned in the OSCP exam** — use manual + Burp there.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and request endpoint checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: detection-ran
    desc: Events and native traffic/session records prove selected-parameter detection and exit
    verify: judge
    evidence: events.jsonl
    on_fail: redo-skill
    required: true
  - id: evidence-captured
    desc: Actual request/response traffic supports any claimed confirmation
    verify: judge
    evidence: evidence/http-traffic.txt
    on_fail: redo-part
    required: false
  - id: data-minimised
    desc: Payloads, scope of testing, omissions and minimum data/proof match actual evidence
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- Reuse reviewed stable input evidence; level/risk escalation needs a lead, not an empty result alone.
- A helper deadline is not proof of a safe negative; incomplete testing remains explicit.
