---
name: burpsuite
description: >
  Use when manually testing a web application with Burp Suite — intercepting proxy, mapping
  the app, Repeater-driven exploitation, Intruder fuzzing, and authz/logic testing. A GUI
  methodology (set scope → proxy/map → Repeater → Intruder → export), the manual hub that
  feeds sqlmap and the vuln-category skills. Not for automated template scanning (use nuclei)
  or pure content discovery (use ffuf).
arguments: "target_or_urls [extension]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: web
domain: web
---

# burpsuite — intercepting proxy & manual web-testing methodology

Shared contract: see AGENTS.md.

## Goal
Manually intercept, inspect, modify, and replay HTTP(S) against an in-scope web app — mapping the
attack surface and driving Repeater/Intruder exploitation (IDOR/authz/logic, injection leads).

## Steps
1. Choose ONE mapping/replay/export hypothesis and a 300-second task allocation. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill burpsuite --profile focused-manual --coverage-set 'Selected manual hypothesis and cases')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; batches use `--targets-file "$HOSTS"`; nonzero STOP. Write notes/task.md; restrict Target/Proxy/Logger to checked hosts before browsing.
2. Verify GUI capability before promising work. No usable GUI -> partial/manual handback, no simulated browsing or wait for interaction. Otherwise use existing context to inspect only relevant pages/parameters; save the actual host tree/cases in evidence/ and notes/sitemap.md with coverage gaps.
3. Repeater tests only the selected authz/logic/injection cases; save real raw request/response files, compare to controls and assess minimum impact. No automatic broad crawler, Intruder cluster-bomb or hidden-parameter spray. A selected low-load Intruder case needs its own finite hypothesis.
4. Export actual cases/project sections and record performed manual work with `python3 -I scripts/otus-log.py event --run-dir "$RUN" --event marker --note "$STEP"`. Markers alone do not prove tests. CLI companions: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 120 -- <verified one-shot argv>` within remaining allocation; no long-lived GUI launch/shell.
5. Record case refs, outcome, omissions and any proposed downstream skill in notes/assessment.md. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected pages and active scanning' --item 'scope-confirmed=ok:../../scope.json' --item 'app-mapped=ok:notes/sitemap.md' --item 'requests-tested=ok:notes/assessment.md'`; only claim actual work/findings, with state/cleanup fields. No findings in tested cases can be complete; unavailable/unfinished GUI work stays partial. Return to coordinator, do not launch sqlmap yourself.

## Modern tooling & alternatives
Burp is standard — **Pro** for active scan/extensions, **Community** for manual Repeater/Intruder
(throttled). `Caido` is a lighter alternative; OWASP `ZAP` the open-source option. For automated
scanning use `nuclei`; for content discovery `ffuf` — Burp is the manual hub tying their output together.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization, endpoints checked, and Burp scope restricted
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: app-mapped
    desc: Relevant observed endpoints/case exports or actual GUI limitation disclosed
    verify: judge
    evidence: notes/sitemap.md
    on_fail: redo-part
    required: true
  - id: requests-tested
    desc: Real exported cases and events support the selected tests, result and omissions
    verify: judge
    evidence: notes/assessment.md
    on_fail: redo-skill
    required: true
  - id: evidence-exported
    desc: Actual request/response files substantiate any claimed impact
    verify: judge
    evidence: notes/assessment.md
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- **Scope first.** Setting Burp's Target scope to in-scope hosts only (and filtering Proxy/Logger) is mandatory before browsing — otherwise you capture/attack out-of-scope traffic; `scope-confirmed` fails hard.
- Return selected captured requests as proposals; Community Edition lacks active scan and throttles Intruder.
- A no-hit run still finishes with `no findings recorded`; findings.md is rendered by the helper.
