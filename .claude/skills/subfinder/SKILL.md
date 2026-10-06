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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope is inherited from `out/<engagement>/scope.txt`.
2. **Passive enumeration** into a clean list: `subfinder -d "$domain" -all -recursive -silent -o "$RUN/subs.txt" | tee -a "$RUN/run.log"`. Add `-oJ -o "$RUN/subs.jsonl"` for a structured record (host + source).
3. **De-dupe / merge (optional).** Fold in other passive sources and keep only new lines with `anew`: `assetfinder --subs-only "$domain" 2>>"$RUN/run.log" | anew "$RUN/subs.txt" >/dev/null`.
4. **Marker + hand-off.** If `subs.txt` is empty, write `no subdomains found` to `findings.md` and ensure a clean empty `subs.txt` (never write the marker into it); else summarize the count. Feed `subs.txt` to `dnsx` → `httpx` → `nuclei`/`katana`. Write `run.json`.

## Modern tooling & alternatives
ProjectDiscovery `subfinder` is the standard for passive discovery. Pair with `amass` (more thorough,
active+passive, slower) and `assetfinder` for extra sources, merging with `anew`; legacy `sublist3r`
is superseded. A provider API-keys config unlocks more passive sources (keep keys untracked).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
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
- A run that finds nothing must still write `findings.md` ("no subdomains found") and a clean empty `subs.txt`.
- Keep `subs.txt` a pure host list fed verbatim to `dnsx`/`httpx` — the marker goes in `findings.md`, never in `subs.txt`.
