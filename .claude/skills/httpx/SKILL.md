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
---

# httpx — HTTP probing & fingerprinting

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the hosts are not confirmed in scope.

Run via the `recon-runner` subagent.

## Goal (desired outcome)
From a host/subdomain list, determine which are live over HTTP(S) and capture title, status
code, tech, IP, and CDN — the "what's actually reachable" filter that narrows the attack surface
before crawling and scanning.

## Steps
1. **Precondition / scope / input.** Confirm the hosts are in scope and point `HOSTS` at the input
   list (usually `subs.txt` from `subfinder` → `dnsx`). Anchor a timestamped run directory to the
   repo root (never write under `skills/`), and fail fast if the input list is missing/empty:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_httpx="${OTUS_RUN_DIR:-$ROOT/out/httpx/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_httpx"
   started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
   mkdir -p "$RUN/notes"
   HOSTS="${1:?path to host list required}"
   [ -s "$HOSTS" ] || { echo "input host list empty/missing: $HOSTS" | tee -a "$RUN/run.log"; exit 1; }
   echo "hosts=$HOSTS confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
2. **Probe live HTTP(S) + fingerprint.** Capture status, title, tech, and IP into a clean list:
   ```bash
   httpx -l "$HOSTS" -title -tech-detect -status-code -ip -o "$RUN/live.txt" | tee -a "$RUN/run.log"
   ```
   Add `-json` for a structured record (status, title, tech, IP, CDN per host):
   ```bash
   httpx -l "$HOSTS" -title -tech-detect -status-code -ip -json -o "$RUN/httpx.jsonl" | tee -a "$RUN/run.log"
   ```
   Stay polite with `-rate-limit <n>` to respect program rate rules.
3. **Split the interesting hosts** — e.g. 200s/redirects and juicy tech — for prioritised follow-up:
   ```bash
   grep -E ' \[(200|30[1278])\]' "$RUN/live.txt" > "$RUN/interesting.txt" 2>/dev/null || true
   ```
4. **Always write a run marker** so "ran but found nothing live" ≠ "didn't run", then summarize:
   ```bash
   count="$( [ -f "$RUN/live.txt" ] && wc -l < "$RUN/live.txt" | tr -d ' ' || echo 0 )"
   if [ "$count" -gt 0 ]; then
     echo "httpx: $count live hosts from $HOSTS" > "$RUN/summary.txt"
   else
     echo "no live hosts" > "$RUN/summary.txt"
     : > "$RUN/live.txt"   # ensure a clean (empty) list file exists for downstream
   fi
   ```
5. **Hand-off.** Feed `live.txt` to `katana` (crawl) → `nuclei` (scan) and `ffuf`
   (ffuf/feroxbuster). Then write the run record `_run.json` into `$RUN/` (schema in Output formats).
6. Hand the run dir to the `reviewer` subagent to verify before treating results as final.

## Modern tooling & alternatives
ProjectDiscovery `httpx` is the standard probe/fingerprinter — **not** the Python `httpx` HTTP
library (ensure the right binary is on PATH). It replaces `httprobe` plus hand-rolled `curl` loops.

## Output formats
Plaintext list (`host [status] [title] [tech] [ip]`) via `-o`; JSON lines (status, title, tech,
IP, CDN) via `-json`. Save the list to `$RUN/live.txt` (and optional `$RUN/httpx.jsonl`). The
executor also writes a run record `$RUN/_run.json`:
```json
{
  "skill": "httpx",
  "target": "<hosts-list>",
  "run_dir": "out/httpx/<timestamp>",
  "started": "<started: date -u +%Y-%m-%dT%H:%M:%SZ, ISO-8601 UTC>",
  "finished": "<finished: date -u at finish; must be >= started>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "probe-ran":        { "attempted": true, "ok": true, "evidence": "summary.txt", "exit": 0 },
    "live-hosts-found": { "attempted": true, "ok": true, "evidence": "live.txt" },
    "handoff-written":  { "attempted": true, "ok": true, "evidence": "live.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (httpx missing, network blocked,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Consumes `subfinder`/`dnsx` output (`subs.txt` / resolved list) and feeds everything downstream:
`katana` (crawl), `nuclei` (scan), and `ffuf`. Pairs with a tech→CVE RAG note to
prioritise hosts by detected stack. No wordlists needed.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Hosts confirmed in scope before probing
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: probe-ran
    desc: HTTP probe executed; run marker written (even if nothing live)
    verify: nonempty
    evidence: summary.txt
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
- `-rate-limit <n>` to stay polite; respect each program's rate rules.
- Feed a resolved/valid host list (`subfinder` → `dnsx`), not raw wildcard noise, or probes waste
  time on dead names.
- A run that finds nothing live must still write `summary.txt` ("no live hosts") and a clean empty
  `live.txt`, so "ran but empty" ≠ "didn't run".
- Keep `live.txt` a clean list fed verbatim downstream — the empty marker goes in `summary.txt`.
- **Save raw evidence to `loot/`** — if a finding (version, status code, response) is used as proof,
  save the raw response to `loot/` (e.g. `curl -s <url> > loot/<name>.html`) so the reviewer can
  hard-verify it.
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/httpx/<timestamp>/` (git-ignored).
