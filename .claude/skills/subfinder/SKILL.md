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
---

# subfinder — passive subdomain discovery

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the apex domain is not confirmed in scope.

Run via the `recon-runner` subagent.

## Goal (desired outcome)
Produce a fast, passive, de-duplicated list of subdomains for an in-scope apex domain as the
first stage of attack-surface mapping — a clean host list ready to resolve and probe downstream.

## Steps
1. **Precondition / scope.** Confirm the apex `domain` is in scope. Record the confirmation so it
   is verifiable, then anchor a timestamped run directory to the repo root (never write under
   `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_subfinder="${OTUS_RUN_DIR:-$ROOT/out/subfinder/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_subfinder"
   mkdir -p "$RUN/notes"
   echo "domain=$domain confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
2. **Passive enumeration.** Pull subdomains from all passive sources, silently, into a clean list:
   ```bash
   subfinder -d "$domain" -all -recursive -silent -o "$RUN/subs.txt" | tee -a "$RUN/run.log"
   ```
   Add `-oJ` for a structured record (JSON lines, with the source per host):
   ```bash
   subfinder -d "$domain" -all -recursive -silent -oJ -o "$RUN/subs.jsonl" | tee -a "$RUN/run.log"
   ```
3. **De-dupe / merge (optional).** Fold in other passive sources (`amass`, `assetfinder`, crt.sh)
   and keep only new lines with `anew`, so `subs.txt` stays a clean, unique host list:
   ```bash
   assetfinder --subs-only "$domain" 2>>"$RUN/run.log" | anew "$RUN/subs.txt" >/dev/null
   ```
4. **Always write a run marker** so "ran but found nothing" ≠ "didn't run", then summarize:
   ```bash
   count="$( [ -f "$RUN/subs.txt" ] && wc -l < "$RUN/subs.txt" | tr -d ' ' || echo 0 )"
   if [ "$count" -gt 0 ]; then
     echo "subfinder: $count subdomains for $domain" > "$RUN/summary.txt"
   else
     echo "no subdomains found" > "$RUN/summary.txt"
     : > "$RUN/subs.txt"   # ensure a clean (empty) list file exists for downstream
   fi
   ```
5. **Hand-off.** Feed `subs.txt` to `dnsx` (resolve/validate) → `httpx` (live HTTP hosts) →
   `nuclei`/`katana`. Then write the run record `_run.json` into `$RUN/` (schema in Output formats).
6. Hand the run dir to the `reviewer` subagent to verify before treating results as final.

## Modern tooling & alternatives
ProjectDiscovery `subfinder` is the standard for passive discovery. Pair it with `amass`
(more thorough, active+passive, slower) and `assetfinder` for extra sources, merging with
`anew`. Legacy `sublist3r` is largely superseded.

## Output formats
Plaintext list (one subdomain per line) via `-o`; JSON lines (host + source) via `-oJ`. Save the
clean list to `$RUN/subs.txt` (and optional `$RUN/subs.jsonl`). The executor also writes a run
record `$RUN/_run.json`:
```json
{
  "skill": "subfinder",
  "target": "<domain>",
  "run_dir": "out/subfinder/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed": { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "enum-ran":        { "attempted": true, "ok": true, "evidence": "summary.txt", "exit": 0 },
    "subdomains-found":{ "attempted": true, "ok": true, "evidence": "subs.txt" },
    "handoff-written": { "attempted": true, "ok": true, "evidence": "subs.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (subfinder missing, network blocked,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Benefits from a provider API-keys config (shared secret store, e.g. `subfinder` provider config)
to unlock more passive sources — keep keys out of tracked files. Consumes an in-scope apex
`domain`; feeds `dnsx` → `httpx` → `nuclei`/`katana`. Pairs with `amass`/`assetfinder`/crt.sh
merged via `anew`. No RAG store needed (config, not knowledge).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Apex domain confirmed in scope before enumeration
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: enum-ran
    desc: Passive enumeration executed; run marker written (even if empty)
    verify: nonempty
    evidence: summary.txt
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
- **Passive only** — low noise and a safe default; it does not actively resolve or brute-force
  DNS (that is `dnsx`/brute skills downstream).
- Rate-limit API sources via the provider config to stay within source limits and program rules.
- A run that legitimately finds nothing must still write `summary.txt` ("no subdomains found")
  and a clean empty `subs.txt`, so "ran but empty" ≠ "didn't run".
- Keep `subs.txt` a pure host list — never write the empty marker into it (it is fed verbatim to
  `dnsx`/`httpx`); the marker goes in `summary.txt`.
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/subfinder/<timestamp>/` (git-ignored).
