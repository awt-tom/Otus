---
name: ssrf
description: >
  Use when testing for server-side request forgery (SSRF) on an authorized web target —
  parameters that make the server fetch a URL, cloud metadata (169.254.169.254), internal
  services, filter bypasses. A testing methodology (param ID → internal targets → bypass →
  impact) using an OOB collaborator and RAG payloads. Not for client-side XSS (use xss).
arguments: "target_or_urls [param]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: web
domain: web
---

# ssrf — server-side request forgery testing methodology

Shared contract: see AGENTS.md.

## Goal
Test selected server-side fetch candidates with minimal proof to already bound destinations.
Do not expand a fetch confirmation into a private-network or metadata sweep.

## Steps
1. Select <=3 URL-fetching candidates and a 120-second initial task. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ssrf --profile selected-fetch --coverage-set 'At most three fetch candidates')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --target "$DESTINATION" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, actual application/destination, input/version and proof criterion.
2. Reuse known parameters and test a minimal callback/banner to an already bound destination. Record candidates in notes/candidates.md. Use existing bounded OOB facilities, not a held listener; lack of callback visibility is inconclusive, not absence of SSRF.
3. Every induced endpoint/redirect needs a fresh gate, including private/metadata IPs. No default metadata/private-range sweep or application-filter bypass ladder; a further test requires a specific lead/new finite allocation. Platform refusals are never bypassed.
4. CLI: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --target "$DESTINATION" --timeout 120 -- <verified one-shot request argv>`; native request timeouts fit remaining allocation. Save actual requests/responses and OOB logs; manual actions need exports/marker events. Record proof or explicit no-confirmation/untested cases in evidence/verification.md; no full credentials or destructive pivot.
5. Complete only selected observed tests; native budget/missing OOB/inconclusive -> partial, hard failure -> error and stop. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other parameters, destinations and filter tests' --item 'scope-confirmed=ok:../../scope.json' --item 'params-identified=ok:notes/candidates.md' --item 'tested=ok:events.jsonl' --item 'confirmed-impact=ok:evidence/verification.md'`; add only real findings and actual state/cleanup fields. Return evidence to coordinator.

## Modern tooling & alternatives
Burp Suite (Repeater + Collaborator) is the manual hub; `interactsh` for standalone OOB; param
discovery via `ffuf`/`katana`/Param Miner. `nuclei` SSRF templates catch known patterns — this skill
covers the manual/bypass reasoning those miss.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope, application, and induced destinations checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: params-identified
    desc: Parameters that trigger server-side outbound requests enumerated
    verify: nonempty
    evidence: notes/candidates.md
    on_fail: redo-part
    required: true
  - id: tested
    desc: Events and raw cases substantiate bounded tests or disclosed untested cases
    verify: judge
    evidence: events.jsonl
    on_fail: redo-skill
    required: true
  - id: confirmed-impact
    desc: Confirmed SSRF has OOB/response proof + minimal impact, no secret exfil (or documented "none")
    verify: judge
    evidence: evidence/verification.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Minimal proof only.** Show reach (callback, metadata endpoint, internal banner) — never dump full cloud credentials or pivot destructively; `confirmed-impact` fails hard (`on_fail: fail`).
- Blind SSRF needs correlated OOB evidence; client requests or a reflected URL do not prove server fetch.
- Application filtering and platform guardrails are different; never retry a refused runtime action.
