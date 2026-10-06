---
name: metasploit
description: >
  Use when exploiting a confirmed, authorized target with the Metasploit Framework
  (msfconsole) — select/configure an exploit or auxiliary module, run `check`, deliver a
  payload, and manage sessions / post-exploitation. Input is service/version detail from
  nmap. Not for content discovery (ffuf) or template scanning (nuclei); prefer single
  searchsploit/GitHub exploits for OSCP-style manual work.
arguments: "target_host [service_or_cve] [lhost]"
model: inherit
effort: medium
context: inline
agent:
category: access
domain: host
---

# metasploit — exploitation framework (msfconsole)

Shared contract: see AGENTS.md.

## Goal
Select, configure, and run the right exploit/auxiliary module against an authorized target — validate
with `check` before firing, deliver a payload, and manage the session, capturing the full transcript.

## Steps
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill metasploit)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Check every RHOSTS entry, not just one; record LHOST and module/options without secrets.
2. Wrap one-shot `msfconsole -q -x "workspace -a <engagement>; search <service/cve>; use <module>; set RHOSTS <target>; set LHOST <you>; set payload <payload>; check; run; sessions -l; exit"` with `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --` (batch: `--targets-file "$HOSTS"`). Only run after a separately inspected check result; the helper replaces the logging-only spool. Record options in `notes/modules.txt`.
3. **`check` before `run`.** Only `run`/`exploit` on a positive (or deliberately-justified) `check`. **Never** Autopwn / browser_autopwn (OSCP-banned, indiscriminate).
4. **Session / post-ex.** On a session: `sessions -i <id>`, run post modules, `migrate`, loot; `db_export -f xml "$RUN/workspace.xml"` to save the workspace.
5. All post-ex commands remain one-shot/helper-wrapped; never hold a REPL/session. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'module-selected=ok:notes/modules.txt' --item 'run-executed=ok:findings.md' --item 'check-before-run=ok:run.log'`; add verified `--finding` proof and actual artifacts/cleanup fields. Summary records `no session` when applicable.

## Modern tooling & alternatives
`msfconsole` is still the standard framework. For manual / OSCP-style work prefer single exploits from
`searchsploit` / ExploitDB / GitHub run by hand; `msfvenom` generates standalone payloads/shellcode
when you don't want the full framework.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and every RHOSTS target checked; LHOST recorded
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: module-selected
    desc: Module searched, selected, and configured (RHOSTS/LHOST/payload) — recorded
    verify: nonempty
    evidence: notes/modules.txt
    on_fail: redo-part
    required: true
  - id: run-executed
    desc: Module executed; run marker written (even if no session opened)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: check-before-run
    desc: '`check` used before `run` where supported; no Autopwn/browser_autopwn (OSCP-banned)'
    verify: judge
    evidence: run.log
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Use `check` before `run`** (avoid noisy auto-exploitation); **Autopwn/browser_autopwn are OSCP-banned** — do not use them. `check-before-run` fails hard (`on_fail: fail`).
- Set `LHOST` to the correct interface for the lab/engagement network, or your payload never calls back.
- Prefer manual searchsploit/GitHub PoCs where appropriate; no session still finishes with a matching summary and module notes.
