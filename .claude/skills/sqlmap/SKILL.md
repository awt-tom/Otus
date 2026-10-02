---
name: sqlmap
description: >
  Use when confirming and exploiting SQL injection (SQLi) on an authorized target with
  sqlmap — DBMS fingerprint, data extraction (--dump), file read, OS shell. Input is a
  captured request (-r req.txt), often from ffuf/Burp-found parameters. Not for generic
  content discovery (use ffuf) or template-based scanning (use nuclei).
arguments: "request_file [level] [risk]"
model: inherit
effort: high
context: inline
agent:
---

# sqlmap — SQL injection detection & exploitation

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the target in the captured request is not confirmed in scope.

## Goal (desired outcome)
Confirm SQLi on an authorized target and, where warranted, exploit it (DBMS fingerprint, dump,
file read, shell) — pulling the **minimum** data needed and recording payloads for the report.

## Steps
1. **Precondition / scope / capture the request.** Save the target request (Burp "save item",
   or craft `req.txt`). Confirm the host is in scope. Anchor a timestamped run directory to the
   repo root (never write under `skills/`); fail fast if the request file is empty:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/sqlmap/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   REQ="${1:?path to captured request file (-r) required}"
   [ -s "$REQ" ] || { echo "request file empty/missing: $REQ" | tee -a "$RUN/run.log"; exit 1; }
   echo "target from $REQ confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/payloads.txt"
   ```
2. **Detect / confirm injection** non-interactively, with capped depth:
   ```bash
   sqlmap -r "$REQ" --batch --level "${2:-3}" --risk "${3:-2}" | tee -a "$RUN/run.log"
   ```
3. **If injectable, enumerate minimally** — fingerprint → `--dbs` → `--tables` → `--dump` only
   what's needed. **Never `--dump` entire databases by default.** Use `--dump-format=csv` for a
   structured capture, and note every payload/table pulled in `notes/payloads.txt`.
4. **Advanced (only if authorized & needed).** `--os-shell`, `--file-read=<path>`, technique
   tuning `--technique=<BEUSTQ>`, and WAF bypass `--tamper=<script>`. These are intrusive — gate
   them on explicit authorization.
5. **Collect evidence + marker.** Copy sqlmap's native session output into the run dir, then
   write the run marker and record (so "ran but nothing" ≠ "didn't run"):
   ```bash
   cp -a "$HOME/.local/share/sqlmap/output/." "$RUN/sqlmap-output/" 2>/dev/null || true
   if grep -qiE "is vulnerable|sqlmap identified|the back-end DBMS is" "$RUN/run.log"; then
     echo "sqlmap: injection confirmed (see run.log + notes/payloads.txt)" > "$RUN/summary.txt"
   else
     echo "no injection confirmed" > "$RUN/summary.txt"
     echo "none" >> "$RUN/notes/payloads.txt"
   fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
`sqlmap` remains the standard for automated SQLi; `ghauri` is a faster newer alternative. For
manual blind SQLi, hand-crafted payloads + Burp Repeater.

## Output formats
CLI tables; sqlmap's own session/logs live under `~/.local/share/sqlmap/output/<host>/` and are
copied into `$RUN/sqlmap-output/`; `--dump-format=csv` for structured dumps. The executor also
writes `$RUN/run.log`, `$RUN/summary.txt`, `$RUN/notes/payloads.txt`, and a run record
`$RUN/_run.json`:
```json
{
  "skill": "sqlmap",
  "target": "<from request_file>",
  "run_dir": "out/sqlmap/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "detection-ran":    { "attempted": true, "ok": true, "evidence": "summary.txt", "exit": 0 },
    "evidence-captured":{ "attempted": true, "ok": true, "evidence": "sqlmap-output" },
    "data-minimised":   { "attempted": true, "ok": true, "evidence": "notes/payloads.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (sqlmap missing, target unreachable,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Pairs with a SQLi payload / tamper RAG (PayloadsAllTheThings) for technique and WAF-bypass
selection. Input often comes from `ffuf` / Burp-found parameters; confirmed findings feed
reporting and further exploitation.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target in the captured request confirmed in scope before any injection attempt
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: detection-ran
    desc: Detection executed; run marker written (even if not injectable)
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: evidence-captured
    desc: sqlmap session output captured into the run directory
    verify: exists
    evidence: sqlmap-output
    on_fail: redo-part
    required: false
  - id: data-minimised
    desc: Only the minimum necessary data was dumped; payloads recorded (no blanket full-DB dump)
    verify: judge
    evidence: notes/payloads.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- `--batch` for non-interactive runs; cap `--level` / `--risk` rather than cranking them blindly.
- **Never `--dump` entire databases by default** — pull the minimum needed and record exactly what
  was extracted in `notes/payloads.txt`; `data-minimised` fails hard (`on_fail: fail`), not retried.
- **Banned in the OSCP exam** — for OSCP-style work use manual payloads + Burp instead.
- Intrusive options (`--os-shell`, `--file-read`, writes) only with explicit authorization; the
  reviewer will not auto-retry them.
- A run that confirms nothing must still write `summary.txt` ("no injection confirmed") and
  `notes/payloads.txt` so "ran but empty" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/sqlmap/<timestamp>/` (git-ignored).
