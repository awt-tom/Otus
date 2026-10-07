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
agent: recon-runner
background: false
category: recon
domain: network
---

# subfinder — passive subdomain discovery

Shared contract: see AGENTS.md.

## Goal
Produce a fast, passive, de-duplicated list of subdomains for an in-scope apex domain — a clean host
list ready to resolve and probe downstream.

## Steps
1. Use only for an actual apex-domain discovery goal; skip an isolated internal IP/.htb host. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill subfinder --target "$domain" --profile passive-quick --coverage-set 'Default passive sources, at most one native minute')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$domain" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, source/version choice, total allocation and escalation trigger.
2. Verify binary/version/help before provider activity: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- subfinder -version`. Inspect supported flags/source configuration; secrets stay out of notes.
3. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$domain" --timeout 75 --grace 5 -- subfinder -d "$domain" -silent -timeout 5 -max-time 1 -o "$RUN/subs.txt"`. Native `-max-time` is minutes; outer slack permits flushing. No default all-source/recursive discovery, extra-tool merge or active DNS brute force.
4. Preserve native subs.txt; save a deduplicated pure host list in notes/hosts.txt. Empty discovery is valid. Assess completed/skipped sources, native stop and limitations in notes/coverage.md; no claims that passive discovery is exhaustive. Every discovered host needs a fresh check before a downstream worker probes it; return the list to the coordinator, do not start httpx.
5. Native early/skipped/inconclusive -> partial with the actual STOP; selected sources finished -> complete/completed; helper failure -> error, stop. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected providers, active DNS and nested discovery' --item 'scope-confirmed=ok:../../scope.json' --item 'enum-ran=ok:events.jsonl' --item 'handoff-written=ok:notes/hosts.txt' --item 'coverage-assessed=ok:notes/coverage.md' --target-state unchanged --cleanup not-needed`; count only observed hosts, not guessed source coverage.

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
    desc: Paired command events and native output substantiate the bounded passive attempt
    verify: judge
    evidence: events.jsonl
    on_fail: redo-skill
    required: true
  - id: handoff-written
    desc: Clean subdomain list file exists for downstream resolve/probe
    verify: judge
    evidence: notes/hosts.txt
    on_fail: redo-part
    required: true
  - id: coverage-assessed
    desc: Source omissions, native stop, health and any deeper-discovery proposal are truthful
    verify: judge
    evidence: notes/coverage.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- Native time limit or failed providers do not establish absence of subdomains. Unknown source counts stay unknown.
- Deeper passive sources require a domain objective/lead and a new finite allocation, not an automatic merge ladder.
