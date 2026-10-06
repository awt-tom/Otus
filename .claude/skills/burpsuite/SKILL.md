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
context: inline
agent:
category: web
domain: web
---

# burpsuite — intercepting proxy & manual web-testing methodology

Shared contract: see AGENTS.md.

## Goal
Manually intercept, inspect, modify, and replay HTTP(S) against an in-scope web app — mapping the
attack surface and driving Repeater/Intruder exploitation (IDOR/authz/logic, injection leads).

## Steps
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill burpsuite)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. For lists use `--targets-file "$HOSTS"`. `mkdir -p "$RUN/requests"`; restrict Burp Target/Proxy/Logger to checked hosts before browsing.
2. **Proxy + map.** Route the browser through Burp, authenticate, and browse/crawl so **Target → Site map** populates; capture mapped endpoints/parameters into `notes/sitemap.md` (export items or paste the host tree) so "mapped" is evidenced.
3. **Repeater — targeted testing.** Send interesting requests to Repeater; test IDOR / broken authz / logic by swapping IDs, tokens, roles and tampering params. Save notable raw request/response into `requests/` (one file per case). Hand injectable params to `sqlmap` (save item → `req.txt`).
4. **Intruder + helpers.** Use Intruder for targeted fuzzing (sniper/cluster-bomb), and Decoder/Comparer/Sequencer as needed. Useful extensions: **Autorize** (authz), **Param Miner** (hidden params), **Logger++**.
5. Export requests/project/report and record each manual step with `python3 -I scripts/otus-log.py event --run-dir "$RUN" --event marker --note "$STEP"`. CLI companions use `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" -- CMD`. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'app-mapped=ok:notes/sitemap.md' --item 'requests-tested=ok:findings.md'`; add verified `--finding` entries referencing saved cases and actual cleanup fields. Use no-findings summary if none.

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
    desc: App proxied/crawled; mapped endpoints captured (not assumed)
    verify: nonempty
    evidence: notes/sitemap.md
    on_fail: redo-part
    required: true
  - id: requests-tested
    desc: Interesting requests tested via Repeater/Intruder; run marker written
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: evidence-exported
    desc: Notable request/response cases saved into the run directory
    verify: exists
    evidence: requests
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- **Scope first.** Setting Burp's Target scope to in-scope hosts only (and filtering Proxy/Logger) is mandatory before browsing — otherwise you capture/attack out-of-scope traffic; `scope-confirmed` fails hard.
- Hand injectable parameters to `sqlmap` (save item → `req.txt`), not hand-brute-forced; Community Edition throttles Intruder and has no active scan, so plan manual/targeted fuzzing.
- A no-hit run still finishes with `no findings recorded`; findings.md is rendered by the helper.
