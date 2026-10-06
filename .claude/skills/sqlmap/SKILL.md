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
1. Save `REQ` and identify its actual endpoint as `TARGET`. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill sqlmap --target "$TARGET")"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Empty requests finalize error before any scan.
2. **Detect:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" -- sqlmap -r "$REQ" --batch --level "${2:-3}" --risk "${3:-2}"`. Every subsequent sqlmap command uses the same wrapper and timeout rules.
3. **If injectable, enumerate minimally** — fingerprint → `--dbs` → `--tables` → `--dump` only what's needed. **Never `--dump` entire databases by default.** `--dump-format=csv` for structured capture; note every payload/table pulled in `notes/payloads.txt`.
4. **Advanced (only if authorized & needed).** `--os-shell`, `--file-read=<path>`, `--technique=<BEUSTQ>`, WAF bypass `--tamper=<script>` — intrusive; gate on explicit authorization.
5. Copy only THIS invocation's session output to `sqlmap-output/`, never unrelated cached targets. Record payloads even if none. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'detection-ran=ok:findings.md' --item 'data-minimised=ok:notes/payloads.txt'`; add verified `--finding` entries and actual target-state/cleanup fields. Use `no injection confirmed` if none.

## Modern tooling & alternatives
`sqlmap` remains the standard for automated SQLi; `ghauri` is a faster newer alternative. For manual
blind SQLi, hand-crafted payloads + Burp Repeater. **Banned in the OSCP exam** — use manual + Burp there.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and request endpoint checked
    verify: judge
    evidence: ../../scope.json
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
- No injection still finishes with that summary and notes/payloads.txt; findings.md is generated.
