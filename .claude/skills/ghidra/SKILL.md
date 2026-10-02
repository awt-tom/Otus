---
name: ghidra
description: >
  Use to statically reverse-engineer an unknown binary with Ghidra — decompile to C-like
  pseudocode, map logic, and find the check/flag/vuln — driving analysis via the GUI methodology
  or the headless analyzeHeadless scripting for automation. Extracted algorithm/constraints feed
  pwntools (exploit) or a z3/script solve. Not for dynamic exploitation (use pwntools/gdb).
arguments: "binary [project_dir] [postScript]"
model: inherit
effort: xhigh
context: inline
agent:
---

# ghidra — reverse engineering suite (decompiler)

**Scope guard:** Authorized CTF / lab / owned binaries only. Only reverse-engineer binaries you are authorized to analyze. Abort if the binary is not in scope.

## Goal (desired outcome)
Statically understand an unknown binary — decompile to readable C-like pseudocode, map the logic, and
extract the check / flag / vulnerability or algorithm/constraints — then hand that understanding to
the exploit or solve step.

## Steps
1. **Precondition / scope / triage.** Confirm the binary is in scope. Anchor a timestamped run
   directory to the repo root (never write under `skills/`) and do quick triage first:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_ghidra="${OTUS_RUN_DIR:-$ROOT/out/ghidra/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_ghidra"
   mkdir -p "$RUN/project" "$RUN/notes"
   BIN="${1:?path to target binary required}"
   echo "binary confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   file "$BIN" | tee "$RUN/notes/triage.txt"; strings -n 8 "$BIN" | head -200 >> "$RUN/notes/triage.txt"
   : > "$RUN/run.log"; : > "$RUN/findings.md"
   ```
2. **Import + auto-analyze.** GUI: import the binary and run auto-analysis. For automation, use the
   headless analyzer (verified flags: `-import`, `-postScript`, `-scriptPath`, `-log`, `-overwrite`,
   `-deleteProject`, `-noanalysis`):
   ```bash
   analyzeHeadless "$RUN/project" ctf -import "$BIN" -log "$RUN/run.log" -overwrite \
     ${3:+-scriptPath "$RUN/scripts" -postScript "$3"}
   ```
3. **Locate interesting code.** Find `main`/entry and notable functions via strings/xrefs (the
   flag check, a comparison, a custom crypto/validation routine).
4. **Read + annotate decompilation.** Work through the decompiled pseudocode, renaming variables and
   adding comments; recover the algorithm / constraints (what input satisfies the check). Record the
   logic and any constants in `findings.md`.
5. **Hand off + marker.** Pass the extracted algorithm/constraints to `pwntools` (exploit) or a
   `z3`/Python script (solve). Always write a run marker so "analyzed but no answer yet" ≠ "didn't
   run":
   ```bash
   grep -qiE '^\- ' "$RUN/findings.md" && echo "ghidra: logic/constraints recorded" > "$RUN/summary.txt" \
     || { echo "analysis in progress — no conclusion yet" > "$RUN/summary.txt"; echo "- in progress" >> "$RUN/findings.md"; }
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
Ghidra (free, NSA) is the default decompiler; `IDA Free`, `Binary Ninja`, `radare2`/`Cutter`,
`rizin` are alternatives. Quick-triage companions: `strings` / `objdump` / `readelf` / `ltrace` /
`strace`. Use **Ghidra headless** (`analyzeHeadless`) to script repetitive analysis.

## Output formats
Decompiled pseudocode + an annotated project (`$RUN/project/`); exported C / notes. This skill also
writes `$RUN/notes/triage.txt`, `$RUN/findings.md` (recovered logic/constraints), `$RUN/summary.txt`
(run marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "ghidra",
  "target": "<binary>",
  "run_dir": "out/ghidra/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "analyzed":         { "attempted": true, "ok": true, "evidence": "project" },
    "logic-extracted":  { "attempted": true, "ok": true, "evidence": "findings.md" },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (Ghidra missing, import fails, out of
scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**High RAG value:** an RE-pattern library (common obfuscations, crypto constants, libc quirks) to
recognise constructs fast. Consumes quick-triage output; feeds `pwntools` (exploit) and crypto/solve
skills (`z3`, Python).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target binary confirmed in scope before analysis
    verify: judge
    evidence: notes/scope.txt
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
    evidence: summary.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **GUI-heavy** — the skill is a *methodology* + headless scripting, not one command; use
  `analyzeHeadless` for automation/batch.
- Quick-triage first (`file`/`strings`/`objdump`) — many CTF binaries give up the flag or a strcmp
  without full decompilation.
- Rename/annotate as you go; the decompiler output is a starting point, not ground truth — verify
  against disassembly on tricky functions.
- Hand the recovered constraints to `z3`/`pwntools` rather than solving by hand.
- A run with no conclusion yet must still write `summary.txt` ("in progress") so "ran but empty" ≠
  "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/ghidra/<timestamp>/` (git-ignored).
