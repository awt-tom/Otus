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
1. Point `HOSTS` at a plain live-host/URL list. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill nuclei)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; on nonzero STOP. Resolve vhosts per AGENTS.md before contact.
2. **Update & verify templates.** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" -- nuclei -update-templates`; confirm the store is non-empty. If the successful update downloaded nothing, wrap `git clone https://github.com/projectdiscovery/nuclei-templates ~/nuclei-templates` with the same helper, then scan with `-t ~/nuclei-templates`. Record the path/count in `notes/templates.txt`; hard failures STOP.
3. **Scan:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" -- nuclei -l "$HOSTS" -severity critical,high,medium -dr -mhe 30 -o "$RUN/nuclei.txt"`. Keep timeout rules from AGENTS.md. `-dr` disables redirects; `-mhe 30` raises max-host-errors. Add `-jsonl`, `-tags cve,takeover,exposure`, `-t <path>`, or bounded `-rate-limit`/`-c` as appropriate.
4. **Marker if empty:** `[ -s "$RUN/nuclei.txt" ] || echo "no findings" > "$RUN/nuclei.txt"` so "found nothing" ≠ "didn't run".
5. **Triage:** verify every hit using helper-wrapped commands with its checked endpoint; write `triage.md`, including no-hit results. Then `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status complete --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'templates-updated=ok:notes/templates.txt' --item 'scan-ran=ok:nuclei.txt' --item 'triaged=ok:triage.md' --target-state unchanged --cleanup not-needed`; add `--finding 'title=...;severity=...;evidence=triage.md'` only for verified hits. Never report raw scanner hits.

## Modern tooling & alternatives
*The* current scanner. Templates live in `~/nuclei-templates` + `/usr/share/nuclei-templates`; write
custom templates for program-specific checks. Companions: `nikto` (server misconfig), `dalfox` (XSS),
`testssl.sh` (TLS).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and every live-list target checked
    verify: judge
    evidence: ../../scope.json
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
