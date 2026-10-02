---
name: nuclei
description: >
  Use when scanning live web hosts for known CVEs, misconfigurations, exposures, and
  subdomain takeovers with nuclei (template-based vulnerability scanner). Consumes the
  httpx live-host list; triage of every hit is mandatory before reporting. Not for
  content discovery (use ffuf) or port scanning (use port-scanner).
arguments: "hosts [severity] [output]"
model: inherit
effort: high
context: fork
agent: general-purpose
---

# nuclei — template-based vulnerability scanner

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the hosts are not confirmed in scope.

Delegate the scan/triage to the `vuln-hunter` subagent.

## Goal (desired outcome)
Scalable, low-false-positive detection of known CVEs, misconfigurations, exposures, and takeovers
across many hosts using community + custom templates — producing a triaged, verified findings set
(never raw scanner output) to drive exploitation and reporting.

## Steps
1. **Precondition / scope / input.** Confirm the hosts are in scope and point `HOSTS` at the live
   list (usually `live.txt` from `httpx`). Anchor a timestamped run directory to the repo root
   (never write under `skills/`); fail fast if the input is empty:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/nuclei/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   HOSTS="${1:?path to live-host list required}"
   [ -s "$HOSTS" ] || { echo "input host list empty/missing: $HOSTS" | tee -a "$RUN/run.log"; exit 1; }
   echo "hosts=$HOSTS confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
   **Optional vhost (DNS).** If the target is reached via a virtual host that does not resolve
   (e.g. `orion.htb`), set `VHOST` so a redirect to it doesn't break the scan. Prefer adding it to
   `/etc/hosts` when `sudo` is available (survives redirects); otherwise fall back to a `Host:`
   header passed on the scan command:
   ```bash
   VHOST="${VHOST:-}"          # optional virtual host, e.g. orion.htb
   HOSTARGS=()                 # extra nuclei args when using a Host header
   if [ -n "$VHOST" ] && ! getent hosts "$VHOST" >/dev/null 2>&1; then
     IP="$(sed -E 's#^https?://##; s#[/:].*$##' "$HOSTS" | head -n1)"
     if command -v sudo >/dev/null 2>&1 && [ -n "$IP" ]; then
       echo "$IP $VHOST" | sudo tee -a /etc/hosts >/dev/null
       echo "vhost: added '$IP $VHOST' to /etc/hosts" | tee -a "$RUN/run.log"
     else
       HOSTARGS=(-H "Host: $VHOST")
       echo "vhost: no sudo/IP, using Host header for $VHOST" | tee -a "$RUN/run.log"
     fi
   fi
   ```
2. **Update & verify templates** before scanning. Run `-update-templates` and record the exit
   code, then confirm the store is non-empty — update can exit 0 yet download nothing, which would
   silently produce an empty scan. If the template count is still 0, clone the repo and scan against
   it with `-t`. Record which path was used:
   ```bash
   nuclei -update-templates | tee -a "$RUN/run.log"; echo "update exit=$?" >> "$RUN/run.log"
   TPLARGS=()                 # add -t only if we fall back to a cloned store
   count="$(find "$HOME/nuclei-templates" /usr/share/nuclei-templates -type f -name '*.yaml' 2>/dev/null | wc -l | tr -d ' ')"
   if [ "$count" -eq 0 ]; then
     echo "templates empty after -update-templates — cloning fallback" | tee -a "$RUN/run.log"
     git clone https://github.com/projectdiscovery/nuclei-templates "$HOME/nuclei-templates" 2>&1 | tee -a "$RUN/run.log"
     TPLARGS=(-t "$HOME/nuclei-templates")
   fi
   echo "templates: count=$count path=${TPLARGS[*]:-default (~/nuclei-templates + /usr/share/nuclei-templates)}" | tee -a "$RUN/notes/templates.txt"
   ```
3. **Scan** the live list at the chosen severities (stay in bounds with `-rate-limit` / `-c`).
   `-dr` disables redirects and `-mhe 30` raises the max host-errors budget, so a redirect-induced
   DNS failure doesn't get the host marked permanently unresponsive and skipped:
   ```bash
   nuclei -l "$HOSTS" "${HOSTARGS[@]}" "${TPLARGS[@]}" -severity critical,high,medium -dr -mhe 30 -o "$RUN/nuclei.txt" | tee -a "$RUN/run.log"
   ```
   Add `-jsonl -o "$RUN/nuclei.jsonl"` for pipelines; narrow with `-tags cve,takeover,exposure`
   or specific `-t <template-path>` checks.
4. **Marker if empty.** Ensure the output file always exists so "found nothing" ≠ "didn't run":
   ```bash
   [ -s "$RUN/nuclei.txt" ] || echo "no findings" > "$RUN/nuclei.txt"
   ```
5. **Triage (mandatory).** Manually verify each hit, drop false positives, and write
   `$RUN/triage.md`. **Never report raw nuclei output.**
6. **Escalate** confirmed findings to exploitation / reporting, then write the run record
   `_run.json` into `$RUN/` (schema in Output formats).
7. Hand the run dir to the `reviewer` subagent to verify before treating results as final.

## Modern tooling & alternatives
*The* 2025–2026 scanner. Templates live in `~/nuclei-templates` + `/usr/share/nuclei-templates`;
write custom templates for program-specific checks. Companions: `nikto` (server misconfig),
`dalfox` (XSS), `testssl.sh` (TLS).

## Output formats
Plaintext (`-o`); `-json` / `-jsonl` for pipelines; `-markdown-export` for reports. Save
`$RUN/nuclei.txt` (+ optional `$RUN/nuclei.jsonl`), the triage in `$RUN/triage.md`, plus a run
record `$RUN/_run.json`:
```json
{
  "skill": "nuclei",
  "target": "<hosts-list>",
  "run_dir": "out/nuclei/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":   { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "templates-updated": { "attempted": true, "ok": true, "exit": 0 },
    "scan-ran":          { "attempted": true, "ok": true, "evidence": "nuclei.txt" },
    "triaged":           { "attempted": true, "ok": true, "evidence": "triage.md" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (nuclei missing, templates update
failed, network blocked, out of scope) set `status: error` and push a line to `errors[]`.

## RAG / shared data / cross-skill
**Strong RAG fit** — index the template library (`~/nuclei-templates` + `/usr/share/nuclei-templates`)
plus CVE notes so the agent picks/writes the right templates. Consumes the `httpx` live list; feeds
manual verification and reporting. Pair with a "custom template authoring" sub-skill.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Hosts confirmed in scope before scanning
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: templates-updated
    desc: nuclei-templates updated before the scan
    verify: exit-zero
    evidence: _run.json#templates-updated
    on_fail: redo-part
    required: true
  - id: scan-ran
    desc: Scan executed against the live-host list (marker written if no findings)
    verify: exists
    evidence: nuclei.txt
    on_fail: redo-skill
    required: true
  - id: triaged
    desc: Findings manually verified / false-positives dropped
    verify: judge
    evidence: triage.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- `-rate-limit` / `-c` concurrency to stay within program bounds.
- **Triage is mandatory** — never report raw nuclei output; `triaged` fails hard (`on_fail: fail`)
  and is not auto-retried.
- Update templates **before** every scan, or you miss recent CVEs and takeover signatures.
- **`-update-templates` can exit 0 yet download nothing** (rate-limited or offline mirror), leaving
  an empty template store and a silently empty scan. Verify the template count first; if it's 0, fall
  back to `git clone https://github.com/projectdiscovery/nuclei-templates ~/nuclei-templates` and
  point the scan at it with `-t ~/nuclei-templates`.
- **Vhost / DNS:** if the host is reached via a virtual host that doesn't resolve (e.g. `orion.htb`),
  a redirect to it fails DNS and the scan breaks — add `<ip> <vhost>` to `/etc/hosts` (preferred;
  survives redirects) or pass `-H "Host: <vhost>"`.
- **Host errors:** use `-dr` (disable redirects) and `-mhe 30` (raise max host errors) so a
  redirect-induced DNS failure doesn't get the host flagged permanently unresponsive and skipped.
- A scan with no hits must still leave `nuclei.txt` ("no findings") so `exists` correctly passes —
  distinguishing "ran, found nothing" from "never ran".
- **Save raw evidence to `loot/`** — if a finding (version, status code, response) is used as proof,
  save the raw response to `loot/` (e.g. `curl -s <url> > loot/<name>.html`) so the reviewer can
  hard-verify it.
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/nuclei/<timestamp>/` (git-ignored).
