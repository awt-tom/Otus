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
context: fork
agent: vuln-hunter
background: false
category: access
domain: host
---

# metasploit — exploitation framework (msfconsole)

Shared contract: see AGENTS.md.

## Goal
Run one applicable exploit/auxiliary hypothesis with minimum verified impact and separate check/run
decisions. A session, payload or post-exploitation ladder is not mandatory.

## Steps
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill metasploit --profile selected-module --coverage-set 'One configured module and separately inspected check/run')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Check every RHOSTS/callback endpoint. Write notes/task.md with matched version, hypothesis, <=300-second total task and <=120-second check/run caps; record verified module/options/effects in notes/modules.txt.
2. Inspect source/options and cheap prerequisites first. Supported check only: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 120 --grace 5 -- msfconsole -q -x "use $MODULE; set RHOSTS $TARGET; check; exit"`; include validated required options, batches with `--targets-file "$HOSTS"`. Save actual transcript refs and applicability in notes/check.md; never combine check and run in one invocation.
3. Inspect the terminal check BEFORE deciding execution. No positive applicability -> partial/no run; unsupported check needs independent evidence and an explicit recorded rationale, not automatic firing. Hard check errors stop. Selected run is a separate helper-wrapped <=120-second one-shot with module-native bounds and minimum proof; no indefinite handler, interactive session, migrate, autopwn or mandatory payload.
4. Record actual module result/raw output, observed coverage and minimal impact in notes/assessment.md and evidence/proof.txt when proved. A console exit zero or session banner alone is not proof. No impact remains partial, not a reason to replay; record created artifacts and remote-job/cleanup uncertainty, never presume local shutdown stopped remote work.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other modules and post-exploitation' --item 'scope-confirmed=ok:../../scope.json' --item 'module-selected=ok:notes/modules.txt' --item 'run-executed=ok:notes/assessment.md' --item 'check-before-run=ok:notes/check.md'`; add only proved findings with actual state/artifacts/cleanup. Return achieved impact or scoped limitations to coordinator.

## Modern tooling & alternatives
`msfconsole` is still the standard framework. For manual / OSCP-style work prefer single exploits from
`searchsploit` / ExploitDB / GitHub run by hand; `msfvenom` generates standalone payloads/shellcode
when you don't want the full framework.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and every RHOSTS target checked; LHOST recorded
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: module-selected
    desc: Exact module/version/options and effects match the selected hypothesis
    verify: judge
    evidence: notes/modules.txt
    on_fail: redo-part
    required: true
  - id: run-executed
    desc: Events/raw output substantiate actual result or justified withheld execution and coverage
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
  - id: check-before-run
    desc: Terminal check independently inspected before run, or unsupported check rationale evidenced
    verify: judge
    evidence: notes/check.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Use `check` before `run`** (avoid noisy auto-exploitation); **Autopwn/browser_autopwn are OSCP-banned** — do not use them. `check-before-run` fails hard (`on_fail: fail`).
- Set `LHOST` to the correct interface for the lab/engagement network, or your payload never calls back.
- Prefer manual searchsploit/GitHub PoCs where appropriate; no session still finishes with a matching summary and module notes.
