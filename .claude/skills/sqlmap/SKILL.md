---
name: sqlmap
description: >
  Use when confirming and exploiting SQL injection (SQLi) on an authorized target with
  sqlmap — DBMS fingerprint, data extraction (--dump), file read, OS shell. Input is a
  captured request (-r req.txt), often from ffuf/Burp-found parameters. Not for generic
  content discovery (use ffuf) or template-based scanning (use nuclei).
arguments: "request_file [level] [risk]"
model: inherit
effort: medium
context: inline
agent:
category: web
domain: web
---

# sqlmap — SQL injection detection & exploitation

Shared contract: see AGENTS.md.

## Goal
Confirm SQLi on an authorized target and, where warranted, exploit it (DBMS fingerprint, dump, file
read, shell) — pulling the **minimum** data needed and recording payloads for the report.

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Save the target request (Burp "save item" or craft `req.txt`); fail fast if `REQ` is empty.
2. **Detect / confirm** non-interactively, with capped depth: `sqlmap -r "$REQ" --batch --level "${2:-3}" --risk "${3:-2}" | tee -a "$RUN/run.log"`.
3. **If injectable, enumerate minimally** — fingerprint → `--dbs` → `--tables` → `--dump` only what's needed. **Never `--dump` entire databases by default.** `--dump-format=csv` for structured capture; note every payload/table pulled in `notes/payloads.txt`.
4. **Advanced (only if authorized & needed).** `--os-shell`, `--file-read=<path>`, `--technique=<BEUSTQ>`, WAF bypass `--tamper=<script>` — intrusive; gate on explicit authorization.
5. **Evidence + marker.** Copy sqlmap's session output into the run dir: `cp -a "$HOME/.local/share/sqlmap/output/." "$RUN/sqlmap-output/" 2>/dev/null || true`. If the log shows a confirmed injection write the marker to `findings.md`, else `no injection confirmed`. Write `run.json`.

## Modern tooling & alternatives
`sqlmap` remains the standard for automated SQLi; `ghauri` is a faster newer alternative. For manual
blind SQLi, hand-crafted payloads + Burp Repeater. **Banned in the OSCP exam** — use manual + Burp there.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
    on_fail: fail
    required: true
  - id: detection-ran
    desc: Detection executed; run marker written (even if not injectable)
    verify: nonempty
    evidence: findings.md
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
- `--batch` for non-interactive runs; cap `--level`/`--risk` rather than cranking them blindly.
- **Never `--dump` entire databases by default** — pull the minimum needed and record exactly what was extracted in `notes/payloads.txt`; `data-minimised` fails hard (`on_fail: fail`).
- Intrusive options (`--os-shell`, `--file-read`, writes) only with explicit authorization.
- A run that confirms nothing must still write `findings.md` ("no injection confirmed") and `notes/payloads.txt`.
