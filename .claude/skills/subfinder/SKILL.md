---
name: subfinder
description: >
  Use when enumerating subdomains of an in-scope apex domain — passive subdomain
  discovery and attack-surface mapping with subfinder (ProjectDiscovery). The first
  recon stage; its subdomain list feeds dnsx → httpx → nuclei/katana. Not for
  port scanning (use port-scanner) or active DNS brute-forcing.
arguments: "domain [output]"
model: inherit
effort: low
context: fork
agent: Explore
category: recon
domain: network
---

# subfinder — passive subdomain discovery

Shared contract: see AGENTS.md.

## Goal
Produce a fast, passive, de-duplicated list of subdomains for an in-scope apex domain — a clean host
list ready to resolve and probe downstream.

## Steps
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill subfinder --target "$domain")"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$domain" --run-dir "$RUN"`; nonzero STOP.
2. **Passive enumeration:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$domain" -- subfinder -d "$domain" -all -recursive -silent -o "$RUN/subs.txt"`. Add `-oJ -o "$RUN/subs.jsonl"` for host/source records.
3. **Optional merge:** export `domain RUN`; `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$domain" -- bash -o pipefail -c 'assetfinder --subs-only "$domain" | anew "$RUN/subs.txt" >/dev/null'`. Check newly discovered hosts before probing them.
4. Keep `subs.txt` a pure host list; summary is count or `no subdomains found`. Feed it to dnsx/httpx. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status complete --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'enum-ran=ok:findings.md' --item 'handoff-written=ok:subs.txt' --target-state unchanged --cleanup not-needed`.

## Modern tooling & alternatives
ProjectDiscovery `subfinder` is the standard for passive discovery. Pair with `amass` (more thorough,
active+passive, slower) and `assetfinder` for extra sources, merging with `anew`; legacy `sublist3r`
is superseded. A provider API-keys config unlocks more passive sources (keep keys untracked).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and apex target checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: enum-ran
    desc: Passive enumeration executed; run marker written (even if empty)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: subdomains-found
    desc: At least one subdomain discovered (empty is a valid outcome)
    verify: min-lines:1
    evidence: subs.txt
    on_fail: redo-part
    required: false
  - id: handoff-written
    desc: Clean subdomain list file exists for downstream resolve/probe
    verify: exists
    evidence: subs.txt
    on_fail: redo-part
    required: true
```

## Notes / pitfalls
- **Passive only** — low noise and a safe default; it does not actively resolve or brute-force DNS (that is `dnsx`/brute skills downstream).
- No discoveries still finish with `no subdomains found` and a clean empty `subs.txt`.
- Keep `subs.txt` a pure host list fed verbatim to `dnsx`/`httpx` — the marker goes in `findings.md`, never in `subs.txt`.
