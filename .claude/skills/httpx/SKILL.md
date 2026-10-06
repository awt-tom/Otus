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
agent: Explore
category: recon
domain: web
---

# httpx — HTTP probing & fingerprinting

Shared contract: see AGENTS.md.

## Goal
From a host/subdomain list, determine which are live over HTTP(S) and capture title, status, tech,
IP, and CDN — the "what's actually reachable" filter that narrows the attack surface before scanning.

## Steps
1. Point `HOSTS` at a plain host list. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill httpx)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP.
2. **Probe:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" -- httpx -l "$HOSTS" -title -tech-detect -status-code -ip -o "$RUN/live.txt"`. Add `-json -o "$RUN/httpx.jsonl"` for structured output or bounded `-rate-limit`.
3. **Split interesting hosts** (200s/redirects, juicy tech) for follow-up: `grep -E ' \[(200|30[1278])\]' "$RUN/live.txt" > "$RUN/interesting.txt" 2>/dev/null || true`.
4. **Hand-off:** keep `live.txt` as raw fingerprint output; save ONLY host/URL tokens to `notes/hosts.txt` for downstream scope checks and nuclei/ffuf. Use summary `no live hosts` if empty. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status complete --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'probe-ran=ok:findings.md' --item 'handoff-written=ok:live.txt' --target-state unchanged --cleanup not-needed`.

## Modern tooling & alternatives
ProjectDiscovery `httpx` is the standard probe/fingerprinter — **not** the Python `httpx` HTTP library
(ensure the right binary is on PATH). It replaces `httprobe` plus hand-rolled `curl` loops.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and every input host checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: probe-ran
    desc: HTTP probe executed; run marker written (even if nothing live)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: live-hosts-found
    desc: At least one live HTTP(S) host found (none is a valid outcome)
    verify: min-lines:1
    evidence: live.txt
    on_fail: redo-part
    required: false
  - id: handoff-written
    desc: Clean live-host list file exists for downstream crawl/scan
    verify: exists
    evidence: live.txt
    on_fail: redo-part
    required: true
```

## Notes / pitfalls
- Use the **ProjectDiscovery** `httpx` binary, not the Python `httpx` library — they are unrelated.
- Feed a resolved/valid host list (`subfinder` → `dnsx`), not raw wildcard noise, or probes waste time on dead names; `-rate-limit <n>` to respect program rules.
- An empty live result still finishes with `no live hosts`; never feed fingerprint annotations to a target checker.
