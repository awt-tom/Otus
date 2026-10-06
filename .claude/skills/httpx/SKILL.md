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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope is inherited from `out/<engagement>/scope.txt`. Point `HOSTS` at the input list (usually `subs.txt`); fail fast if empty: `[ -s "$HOSTS" ] || { echo "input empty: $HOSTS"; exit 1; }`.
2. **Probe live HTTP(S) + fingerprint:** `httpx -l "$HOSTS" -title -tech-detect -status-code -ip -o "$RUN/live.txt" | tee -a "$RUN/run.log"`. Add `-json -o "$RUN/httpx.jsonl"` for a structured record; `-rate-limit <n>` to stay polite.
3. **Split interesting hosts** (200s/redirects, juicy tech) for follow-up: `grep -E ' \[(200|30[1278])\]' "$RUN/live.txt" > "$RUN/interesting.txt" 2>/dev/null || true`.
4. **Marker + hand-off.** If `live.txt` is empty, write `no live hosts` to `findings.md` and ensure a clean empty `live.txt`; else summarize the count. Feed `live.txt` to `katana` (crawl) → `nuclei` (scan) and `ffuf`. Write `run.json`.

## Modern tooling & alternatives
ProjectDiscovery `httpx` is the standard probe/fingerprinter — **not** the Python `httpx` HTTP library
(ensure the right binary is on PATH). It replaces `httprobe` plus hand-rolled `curl` loops.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
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
- A run that finds nothing live must still write `findings.md` ("no live hosts") and a clean empty `live.txt`; keep `live.txt` a clean list fed verbatim downstream.
