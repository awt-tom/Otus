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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Gather `nmap` service/version; determine the correct `LHOST` for the lab network.
2. **Drive msfconsole non-interactively** (one-shot `-x`, no REPL — AGENTS.md): `msfconsole -q -x "spool $RUN/run.log; workspace -a <engagement>; search <service/cve>; use <module>; set RHOSTS <target>; set LHOST <you>; set payload <payload>; check; run; sessions -l; exit"`. Record the chosen module + options in `notes/modules.txt`.
3. **`check` before `run`.** Only `run`/`exploit` on a positive (or deliberately-justified) `check`. **Never** Autopwn / browser_autopwn (OSCP-banned, indiscriminate).
4. **Session / post-ex.** On a session: `sessions -i <id>`, run post modules, `migrate`, loot; `db_export -f xml "$RUN/workspace.xml"` to save the workspace.
5. **Marker + run record.** If `run.log` shows a session opened write the marker to `findings.md`, else `no session — module(s) tried`. Write `run.json`.

## Modern tooling & alternatives
`msfconsole` is still the standard framework. For manual / OSCP-style work prefer single exploits from
`searchsploit` / ExploitDB / GitHub run by hand; `msfvenom` generates standalone payloads/shellcode
when you don't want the full framework.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited); LHOST set for the lab network
    verify: judge
    evidence: ../../scope.txt
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
- For OSCP-style manual work prefer single `searchsploit`/GitHub exploits; a run that opens no session must still write `findings.md` ("no session …") and `notes/modules.txt`.
