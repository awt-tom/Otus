---
name: pwntools
description: >
  Use for binary-exploitation / pwn challenges — script interaction with a local or remote binary
  and build a working exploit (I/O, packing, offsets, ROP, shellcode, format-string) with the
  pwntools Python framework. Iterate local-first, then fire remote to capture the flag. Pairs with
  ghidra/radare2 for the static side.
arguments: "binary [remote_host] [remote_port]"
model: inherit
effort: high
context: fork
agent: vuln-hunter
background: false
category: re-forensics
domain: binary
---

# pwntools — exploit development framework (Python)

Shared contract: see AGENTS.md.

## Goal
Build a working, reproducible exploit for a pwn challenge — model the binary's I/O, defeat its
mitigations, deliver a payload — tested locally first, then fired at the remote to capture the flag.

## Steps
1. Local-first: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill pwntools --profile selected-local --coverage-set 'One binary hypothesis, local-first proof and conditional remote test')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Verify BIN/provenance/tool/libc; write notes/task.md with hypothesis, <=300-second total initial task, <=60-second per-attempt cap and useful-progress/stop criterion. Helper-wrap selected checksec/ELF triage with <=30-second cap into notes/checksec.txt.
2. Save reproducible exploit.py with explicit local/remote inputs, bounded connection/I/O (`context.timeout = 3`, explicit recv deadlines), finite attempt count and `finally: io.close()`; no interactive(), debugger attachment, unbounded receive or held shell. Match the actual binary/libc, derive offsets/leaks from captured evidence rather than guessed magic values.
3. Local attempt: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 60 --grace 5 -- python3 "$RUN/exploit.py" BIN="$BIN" > "$RUN/loot/local-proof.txt"`. Preserve failed transcripts; local hard failure stops this run, no hidden automatic retries. Further local reasoning/tests need a documented meaningful delta and new finite task, not endless exploit cycling.
4. Remote only after local applicability/proof and remaining allocation: `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$HOST" --run-dir "$RUN"`; then `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$HOST" --timeout 60 --grace 5 -- python3 "$RUN/exploit.py" BIN="$BIN" HOST="$HOST" PORT="$PORT" > "$RUN/loot/remote-proof.txt"`. Every actual endpoint is checked; successful delivery is not impact proof. Use one-shot identity/flag capture, not a shell/listener.
5. Record actual attempted/omitted coverage, native outcome, identity/access proof and limitations in notes/assessment.md; flags remain private loot/. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other techniques and untested remote cases' --item 'scope-confirmed=ok:../../scope.json' --item 'binary-triaged=ok:notes/checksec.txt' --item 'exploit-built=ok:exploit.py' --item 'result-recorded=ok:notes/assessment.md'`; finished selected proof can be complete, unresolved/no claimed impact partial, hard failure error. Include only real findings/state/cleanup and hand back to coordinator.

## Modern tooling & alternatives
`pwntools` + `gdb` with `pwndbg`/`GEF`; `ROPgadget`/`ropper` for gadgets; `one_gadget` for libc one-shot
shells; `angr` for symbolic execution; `checksec` for mitigations. Pair with `ghidra`/`radare2` for the static side.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and binary provenance; remote endpoint checked if used
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: binary-triaged
    desc: checksec captured (RELRO/NX/PIE/canary) to drive technique choice
    verify: nonempty
    evidence: notes/checksec.txt
    on_fail: redo-part
    required: true
  - id: exploit-built
    desc: Reproducible exploit script written (local-first, remote-switchable)
    verify: judge
    evidence: exploit.py
    on_fail: fail
    required: true
  - id: result-recorded
    desc: Actual transcript/identity/access evidence supports result and all unfinished work disclosed
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Highest-reasoning class** — a wrong step wastes a run; iterate **local-first**, only then fire remote.
- Keep offsets/leaks **reproducible** (cyclic patterns, scripted leaks) — don't hand-tune magic numbers you can't re-derive.
- Match the challenge libc exactly (provided libc / `pwninit`); a wrong libc breaks ret2libc / one_gadget offsets. `checksec` first — mitigations decide the whole approach.
- No flag yet finishes as partial with `in progress`; flags never enter descriptions or event notes.
