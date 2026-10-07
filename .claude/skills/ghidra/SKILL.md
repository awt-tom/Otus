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
context: fork
agent: vuln-hunter
background: false
category: re-forensics
domain: binary
---

# ghidra — reverse engineering suite (decompiler)

Shared contract: see AGENTS.md.

## Goal
Statically understand an unknown binary — decompile to readable C-like pseudocode, map the logic, and
extract the check / flag / vulnerability or algorithm/constraints — then hand it to the exploit or solve step.

## Steps
1. Offline artifact: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ghidra --profile selected-logic --coverage-set 'Binary triage and selected relevant functions')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Verify nonempty BIN/provenance, installed Ghidra/Java/help. Write notes/task.md with hypothesis/function leads and finite total allocation; cheap <=30-second helper-wrapped file/strings/readelf triage first, save notes/triage.txt.
2. Only if needed, one import/analysis: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 300 --grace 5 -- analyzeHeadless "$RUN/project" otus -import "$BIN" -analysisTimeoutPerFile 240 -log "$RUN/evidence/ghidra.log"`. Create private project/ first, no overwrite. Validate supported native budget and optional locally reviewed postScript before launch. Native analysis timeout can still exit zero; log/selected-function state controls completeness.
3. Inspect entry/string xrefs and selected comparison/validation functions only, not every function. GUI work needs real exports/marker events; unavailable GUI or unbounded script -> no pretend analysis. Keep source addresses and cross-check decompilation against disassembly in notes/logic.md, with actual export refs under evidence/.
4. Record actual import/analysis status, examined functions, omitted work and confidence/unknowns in notes/assessment.md. Secret constants/flags stay in private raw evidence, not descriptions. Reuse reviewed unchanged analysis rather than reimporting the same binary; unresolved logic is partial, not a fabricated vulnerability.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected functions and dynamic exploitation' --item 'scope-confirmed=ok:../../scope.json' --item 'analyzed=ok:notes/assessment.md' --item 'logic-extracted=ok:notes/logic.md' --item 'results-recorded=ok:notes/assessment.md' --target-state unchanged --cleanup not-needed`; complete only actually resolved selected work, native timeout/inconclusive partial, helper failure error. Add only real logic-backed findings; return constraints/next hypothesis to coordinator, no child skill.

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
    desc: Actual log/project/function state proves claimed import/analysis, not directory existence
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
  - id: logic-extracted
    desc: Decompiled logic / constraints recorded (or documented "in progress")
    verify: judge
    evidence: notes/logic.md
    on_fail: redo-part
    required: true
  - id: results-recorded
    desc: Examined/omitted functions, native timeouts and actual conclusions accurately assessed
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **GUI-heavy** — this skill is a *methodology* + headless scripting, not one command; use `analyzeHeadless` for automation/batch.
- Quick-triage first (`file`/`strings`/`objdump`) — many CTF binaries give up the flag or a strcmp without full decompilation.
- Rename/annotate as you go; decompiler output is a starting point, not ground truth — verify against disassembly on tricky functions. Hand recovered constraints to `z3`/`pwntools` rather than solving by hand.
- No conclusion finishes as partial with an `in progress` summary.
