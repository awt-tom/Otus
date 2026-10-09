---
name: httpx
description: >
  Use when probing a host/subdomain list to find which are live over HTTP(S) and
  fingerprint them — status code, title, tech, IP, CDN — with httpx (ProjectDiscovery,
  not the Python httpx library). The "what's actually reachable" filter between
  subfinder/dnsx and katana/nuclei. Not for port scanning (use port-scanner) or
  subdomain discovery (use subfinder).
arguments: "hosts [output]"
model: inherit
effort: low
context: fork
agent: recon-runner
background: false
category: recon
domain: web
---

# httpx — HTTP probing & fingerprinting

Shared contract: see AGENTS.md.

## Goal
From a host/subdomain list, determine which are live over HTTP(S) and capture title, status, tech,
IP, and CDN — the "what's actually reachable" filter that narrows the attack surface before scanning.

## Steps
1. Use a small HOSTS batch of explicit scheme/host:port URLs from known services; no fingerprint annotations. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill httpx --profile known-web --coverage-set 'Selected explicit HTTP(S) endpoints')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with input count, hypothesis, allocation and progress criterion.
2. Resolve HTTPX to the verified ProjectDiscovery executable (possibly `httpx-toolkit`) before contact, once per work period. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- "$HTTPX" -version`; inspect identity and installed help/options. A wrong Python CLI or missing binary is an error, not a reason to retry another executable after failure.
3. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" --timeout 60 --grace 5 -- "$HTTPX" -l "$HOSTS" -no-fallback-scheme -title -tech-detect -status-code -ip -json -threads 5 -rate-limit 10 -timeout 5 -retries 0 -no-stdin -o "$RUN/evidence/httpx.jsonl"`. No unchecked redirects, extracted-domain probes or unbounded retries.
4. Preserve native JSONL; derive clean deduplicated URLs with scheme/port intact:
  `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- python3 -c 'import json,sys; records=map(json.loads,filter(str.strip,open(sys.argv[1]))); urls=dict.fromkeys(record["url"] for record in records if record.get("url")); sys.stdout.write("".join(url+"\n" for url in urls))' "$RUN/evidence/httpx.jsonl" > "$RUN/notes/urls.txt"`.
5. For a specific web lead and remaining allocation, inspect at most three root/robots/sitemap/observed-link responses: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$URL" --timeout 10 -- curl --connect-timeout 3 --max-time 5 -sS -D "$RUN/evidence/headers.txt" -o "$RUN/evidence/page.txt" "$URL"`; use distinct filenames, no followed unchecked redirects. Save actual fingerprints, errors/unknown metrics, omissions and next candidate in notes/coverage.md. Empty results mean no live results observed, not proof every input is dead.
6. Return notes/urls.txt to the coordinator for fresh endpoint gates, never start a scanner. Complete only the finished declared batch; native skip/inconclusive is partial, hard failure error. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected schemes, ports and pages' --item 'scope-confirmed=ok:../../scope.json' --item 'probe-ran=ok:events.jsonl' --item 'handoff-written=ok:notes/urls.txt' --item 'coverage-assessed=ok:notes/coverage.md' --target-state unchanged --cleanup not-needed`; unavailable observed counts remain unknown.

## Modern tooling & alternatives
ProjectDiscovery `httpx` is the standard probe/fingerprinter — **not** the Python `httpx` HTTP library
(ensure the right binary is on PATH). It replaces `httprobe` plus hand-rolled `curl` loops.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and every input host checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: probe-ran
    desc: Verified binary and paired events/native JSONL substantiate the selected probe
    verify: judge
    evidence: events.jsonl
    on_fail: redo-skill
    required: true
  - id: handoff-written
    desc: Clean deduplicated URL list matches JSONL and retains schemes and ports; empty is valid
    verify: judge
    evidence: notes/urls.txt
    on_fail: redo-part
    required: true
  - id: coverage-assessed
    desc: Endpoint coverage, identity, health and follow-up observations match raw evidence
    verify: judge
    evidence: notes/coverage.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- Preflight identity before any target request; do not discover a binary collision halfway through enumeration.
- Unknown metrics stay unknown. A redirect URL is a lead that requires its own scope check, not permission to follow it.
