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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/project" "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Triage first: `file "$BIN" | tee "$RUN/notes/triage.txt"; strings -n 8 "$BIN" | head -200 >> "$RUN/notes/triage.txt"`.
2. **Import + auto-analyze.** GUI: import + run auto-analysis. Headless automation (verified flags `-import -postScript -scriptPath -log -overwrite -deleteProject -noanalysis`): `analyzeHeadless "$RUN/project" ctf -import "$BIN" -log "$RUN/run.log" -overwrite` (add `-scriptPath "$RUN/scripts" -postScript "$3"` to run a script).
3. **Locate interesting code.** Find `main`/entry and notable functions via strings/xrefs (the flag check, a comparison, a custom crypto/validation routine).
4. **Read + annotate decompilation.** Work through the pseudocode, renaming variables + adding comments; recover the algorithm / constraints (what input satisfies the check). Record the logic + constants in `findings.md`.
5. **Hand off + marker + run record.** Pass the extracted algorithm/constraints to `pwntools` (exploit) or a `z3`/Python solve. Write a run marker (`- in progress` if no conclusion), then `run.json`.

## Modern tooling & alternatives
Ghidra (free, NSA) is the default decompiler; `IDA Free`, `Binary Ninja`, `radare2`/`Cutter`, `rizin`
are alternatives. Quick-triage companions: `strings`/`objdump`/`readelf`/`ltrace`/`strace`. Use **Ghidra headless** (`analyzeHeadless`) to script repetitive analysis.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); binary authorized for analysis
    verify: judge
    evidence: ../../scope.txt
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
- A run with no conclusion yet must still write a `- in progress` marker in `findings.md`.
