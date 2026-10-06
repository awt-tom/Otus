---
name: ghidra
description: >
  Use to statically reverse-engineer an unknown binary with Ghidra — decompile to C-like
  pseudocode, map logic, and find the check/flag/vuln — driving analysis via the GUI methodology
  or the headless analyzeHeadless scripting for automation. Extracted algorithm/constraints feed
  pwntools (exploit) or a z3/script solve. Not for dynamic exploitation (use pwntools/gdb).
arguments: "binary [project_dir] [postScript]"
model: inherit
effort: high
context: inline
agent:
category: re-forensics
domain: binary
---

# ghidra — reverse engineering suite (decompiler)

Shared contract: see AGENTS.md.

## Goal
Statically understand an unknown binary — decompile to readable C-like pseudocode, map the logic, and
extract the check / flag / vulnerability or algorithm/constraints — then hand it to the exploit or solve step.

## Steps
1. Offline artifact: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ghidra)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. `mkdir -p "$RUN/project"`. Helper-wrap `file "$BIN"` / `strings -n 8 "$BIN"`, saving triage to `notes/triage.txt`.
2. **Import/analyse:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- analyzeHeadless "$RUN/project" ctf -import "$BIN" -log "$RUN/evidence/ghidra.log" -overwrite`; original optional `-scriptPath "$RUN/scripts" -postScript "$3"`. GUI analysis saves exports and helper marker events instead.
3. **Locate interesting code.** Find `main`/entry and notable functions via strings/xrefs (the flag check, a comparison, a custom crypto/validation routine).
4. **Annotate:** save recovered logic/constraints and disassembly cross-checks in `notes/logic.md`; secret constants/flags remain private evidence, not descriptions.
5. Hand off to pwntools/z3/solve. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'analyzed=ok:project' --item 'logic-extracted=ok:findings.md' --item 'results-recorded=ok:findings.md' --target-state unchanged --cleanup not-needed`; add `--finding` referencing logic evidence. Inconclusive work is partial with `in progress`, not completed analysis.

## Modern tooling & alternatives
Ghidra (free, NSA) is the default decompiler; `IDA Free`, `Binary Ninja`, `radare2`/`Cutter`, `rizin`
are alternatives. Quick-triage companions: `strings`/`objdump`/`readelf`/`ltrace`/`strace`. Use **Ghidra headless** (`analyzeHeadless`) to script repetitive analysis.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and binary provenance checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: analyzed
    desc: Binary imported and auto-analyzed (GUI or headless project created)
    verify: exists
    evidence: project
    on_fail: redo-skill
    required: true
  - id: logic-extracted
    desc: Decompiled logic / constraints recorded (or documented "in progress")
    verify: nonempty
    evidence: findings.md
    on_fail: redo-part
    required: true
  - id: results-recorded
    desc: Run marker written (even when no conclusion yet)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **GUI-heavy** — this skill is a *methodology* + headless scripting, not one command; use `analyzeHeadless` for automation/batch.
- Quick-triage first (`file`/`strings`/`objdump`) — many CTF binaries give up the flag or a strcmp without full decompilation.
- Rename/annotate as you go; decompiler output is a starting point, not ground truth — verify against disassembly on tricky functions. Hand recovered constraints to `z3`/`pwntools` rather than solving by hand.
- No conclusion finishes as partial with an `in progress` summary.
