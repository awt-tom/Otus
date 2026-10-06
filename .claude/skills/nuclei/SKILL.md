---
name: nuclei
description: >
  Use when scanning live web hosts for known CVEs, misconfigurations, exposures, and
  subdomain takeovers with nuclei (template-based vulnerability scanner). Consumes the
  httpx live-host list; triage of every hit is mandatory before reporting. Not for
  content discovery (use ffuf) or port scanning (use port-scanner).
arguments: "hosts [severity] [output]"
model: inherit
effort: medium
context: fork
agent: general-purpose
category: web
domain: web
---

# nuclei — template-based vulnerability scanner

Shared contract: see AGENTS.md.

## Goal
Scalable, low-false-positive detection of known CVEs, misconfigurations, exposures, and takeovers
across many hosts — producing a triaged, verified findings set (never raw scanner output).

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Point `HOSTS` at the live list (usually `live.txt`); fail fast if empty. If the target is reached via a vhost that doesn't resolve, resolve it per AGENTS.md (`/etc/hosts` or `-H "Host: <vhost>"`).
2. **Update & verify templates.** `nuclei -update-templates`, then confirm the store is non-empty — update can exit 0 yet download nothing, silently producing an empty scan. If the count is 0, clone and scan with `-t`: `git clone https://github.com/projectdiscovery/nuclei-templates ~/nuclei-templates` → `-t ~/nuclei-templates`. Record which path was used in `notes/templates.txt`.
3. **Scan** the live list at chosen severities: `nuclei -l "$HOSTS" -severity critical,high,medium -dr -mhe 30 -o "$RUN/nuclei.txt" | tee -a "$RUN/run.log"`. `-dr` disables redirects and `-mhe 30` raises the max-host-errors budget so a redirect-induced DNS failure doesn't get the host skipped. Add `-jsonl`, narrow with `-tags cve,takeover,exposure` or `-t <path>`; `-rate-limit`/`-c` to stay in bounds.
4. **Marker if empty:** `[ -s "$RUN/nuclei.txt" ] || echo "no findings" > "$RUN/nuclei.txt"` so "found nothing" ≠ "didn't run".
5. **Triage (mandatory).** Manually verify each hit, drop false positives, write `$RUN/triage.md`. **Never report raw nuclei output.** Escalate confirmed findings; write `run.json`.

## Modern tooling & alternatives
*The* current scanner. Templates live in `~/nuclei-templates` + `/usr/share/nuclei-templates`; write
custom templates for program-specific checks. Companions: `nikto` (server misconfig), `dalfox` (XSS),
`testssl.sh` (TLS).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
    on_fail: fail
    required: true
  - id: templates-updated
    desc: nuclei-templates updated and verified non-empty before the scan
    verify: nonempty
    evidence: notes/templates.txt
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
- **Triage is mandatory** — never report raw nuclei output; `triaged` fails hard (`on_fail: fail`).
- Update templates **before** every scan, but **`-update-templates` can exit 0 yet download nothing** (rate-limited/offline mirror) — verify the count first and `git clone` the templates repo as a fallback.
- **Vhost / host errors:** a redirect to a non-resolving vhost breaks DNS — resolve per AGENTS.md; use `-dr` + `-mhe 30` so the host isn't flagged permanently unresponsive and skipped.
- A scan with no hits must still leave `nuclei.txt` ("no findings") so `exists` passes.
