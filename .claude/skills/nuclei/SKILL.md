---
name: nuclei
description: >
  Use when scanning live web hosts for known CVEs, misconfigurations, exposures, and
  subdomain takeovers with nuclei (template-based vulnerability scanner). Consumes the
  httpx live-host list; triage of every hit is mandatory before reporting. Not for
  content discovery (use ffuf) or port scanning (use port-scanner).
arguments: "hosts [severity] [output]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: web
domain: web
---

# nuclei — template-based vulnerability scanner

Shared contract: see AGENTS.md.

## Goal
Test a small technology-relevant set of cached templates and independently triage each hit.
No hits means only no confirmed result in the declared template/endpoint set.

## Steps
1. Use a small plain HOSTS URL list. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill nuclei --profile selected-templates --coverage-set 'At most 20 technology-relevant cached templates')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, endpoint count, 180-second command allocation and escalation trigger.
2. Verify installed Nuclei/version/help and cached templates locally; no per-target update/clone. Record exact <=20 selected template paths/versions and applicability in notes/templates.txt; TEMPLATES names only those paths, not an entire store. Inspect induced endpoints and exclude code/headless/DoS/brute/fuzz behavior. No authorized usable cache -> setup limitation, no scan.
3. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" --timeout 180 --grace 5 -- nuclei -l "$HOSTS" -t "$TEMPLATES" -c 2 -bs 1 -rate-limit 10 -timeout 5 -retries 0 -mhe 5 -dr -ni -duc -no-stdin -jsonl -o "$RUN/evidence/nuclei.jsonl"`. Disable redirects/OOB/update checks; every induced destination must remain checked. An explicitly authorized collaborator is a separate justified configuration.
4. Preserve empty native JSONL unchanged. Read completion/skip/error counters from raw output, assess native host/template skips and actual coverage in notes/coverage.md; exit zero alone is not full coverage. Unknown counts remain unknown; stop heavy work on degraded health. Broader template sets need a matched lead or declared assessment coverage requirement, not severity broadening alone.
5. Verify each candidate with a minimal checked request within the task allocation; save raw requests/responses and notes/triage.md, including scoped no-hit/false-positive results. Verification CLI: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 15 -- <verified one-shot argv>`. If allocation ends before triage, remain partial and do not claim an unverified finding.
6. Complete only the actually finished selected task; native skips/budget -> partial, hard failure -> error and stop. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected templates and endpoints' --item 'scope-confirmed=ok:../../scope.json' --item 'templates-selected=ok:notes/templates.txt' --item 'scan-ran=ok:events.jsonl' --item 'triaged=ok:notes/triage.md' --item 'coverage-assessed=ok:notes/coverage.md'`; add only evidence-backed findings and actual target-state/cleanup fields. Return to coordinator for review.

## Modern tooling & alternatives
Use locally reviewed/versioned templates; updates are separate setup work, not a per-target stage.
Minimal manual requests confirm candidates without a broad scanner chain.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and every live-list target checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: templates-selected
    desc: Selected cached paths/version/applicability and induced endpoints verified before contact
    verify: judge
    evidence: notes/templates.txt
    on_fail: redo-part
    required: true
  - id: scan-ran
    desc: Paired events and unchanged native output substantiate the bounded attempt
    verify: judge
    evidence: events.jsonl
    on_fail: redo-skill
    required: true
  - id: triaged
    desc: Findings manually verified / false-positives dropped
    verify: judge
    evidence: notes/triage.md
    on_fail: fail
    required: true
  - id: coverage-assessed
    desc: Actual/skipped templates and hosts, health and omissions accurately disclosed
    verify: judge
    evidence: notes/coverage.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- Never put markers into native JSONL or equate scanner severity with confirmed impact.
- High host-error allowances hide degraded targets; report skips instead of scanning through failures.
