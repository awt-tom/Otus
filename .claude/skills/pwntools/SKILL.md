---
name: pwntools
description: >
  Use for binary-exploitation / pwn challenges — script interaction with a local or remote binary
  and build a working exploit (I/O, packing, offsets, ROP, shellcode, format-string) with the
  pwntools Python framework. Highest-reasoning skill class (effort max); iterate local-first, then
  fire remote to capture the flag. Pairs with ghidra/radare2 for the static side.
arguments: "binary [remote_host] [remote_port]"
model: inherit
effort: max
context: inline
agent:
---

# pwntools — exploit development framework (Python)

**Scope guard:** Authorized CTF / lab / owned binaries only. Only develop and run exploits against challenge binaries and endpoints you are authorized to attack. Abort if the binary or remote endpoint is not in scope.

## Goal (desired outcome)
Build a working, reproducible exploit for a pwn challenge — modelling the binary's I/O, defeating its
mitigations, and delivering a payload — tested locally first, then fired at the remote to capture the
flag.

## Steps
1. **Precondition / scope / checksec.** Confirm the binary/endpoint are in scope. Anchor a
   timestamped run directory to the repo root (never write under `skills/`) and record the binary's
   mitigations (`checksec` → RELRO/NX/PIE/canary) — they dictate the technique:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_pwntools="${OTUS_RUN_DIR:-$ROOT/out/pwntools/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_pwntools"
   mkdir -p "$RUN/notes"
   BIN="${1:?path to target binary required}"
   echo "binary/endpoint confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   checksec "$BIN" 2>&1 | tee "$RUN/notes/checksec.txt" | tee -a "$RUN/run.log"
   ```
2. **Model I/O.** Start the exploit script against the local process, switching to remote via an
   argument so the same script targets both:
   ```python
   # $RUN/exploit.py
   from pwn import *
   context.binary = exe = ELF(args.BIN or "./chall")
   context.log_level = "info"
   io = remote(args.HOST, int(args.PORT)) if args.HOST else process(exe.path)
   ```
3. **Find the offset / leak.** Use `cyclic`/`cyclic_find` to locate the overflow offset; leak
   addresses (GOT/libc) and defeat mitigations (canary, PIE, ASLR) as needed. Keep offsets/leaks
   reproducible and noted in `notes/`.
4. **Build the payload.** Construct the exploit with `ROP(exe)`, `shellcraft`, `p64()`/`flat()` —
   ret2libc / ret2csu / ret2dlresolve / format-string per the challenge. Debug with
   `gdb.attach(io)` (pwndbg/GEF), `ROPgadget`/`ropper` for gadgets, `one_gadget` for libc shells.
5. **Local → remote + capture.** Get a shell/flag locally, then flip to `HOST`/`PORT` and capture:
   ```bash
   python3 "$RUN/exploit.py" BIN="$BIN"                                 2>&1 | tee -a "$RUN/run.log"   # local
   python3 "$RUN/exploit.py" BIN="$BIN" HOST="${2:-}" PORT="${3:-}"     2>&1 | tee -a "$RUN/run.log"   # remote
   grep -oE '([A-Za-z0-9_]+\{[^}]+\}|flag\{[^}]+\})' "$RUN/run.log" | sort -u > "$RUN/flag.txt" || true
   [ -s "$RUN/flag.txt" ] && echo "pwntools: flag captured" > "$RUN/summary.txt" || echo "no flag yet — exploit in progress" > "$RUN/summary.txt"
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
`pwntools` + `gdb` with `pwndbg` or `GEF`; `ROPgadget` / `ropper` for gadgets; `one_gadget` for libc
one-shot shells; `angr` for symbolic execution; `checksec` for mitigations. Pair with `ghidra` /
`radare2` for the static side (understanding the vuln before scripting it).

## Output formats
The exploit script itself (`$RUN/exploit.py`) + the captured flag (`$RUN/flag.txt`); structured logs
via `context.log_level`. This skill also writes `$RUN/notes/checksec.txt`, `$RUN/summary.txt` (run
marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "pwntools",
  "target": "<binary>[ @ host:port]",
  "run_dir": "out/pwntools/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed": { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "binary-triaged":  { "attempted": true, "ok": true, "evidence": "notes/checksec.txt" },
    "exploit-built":   { "attempted": true, "ok": true, "evidence": "exploit.py" },
    "result-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (pwntools missing, binary unreadable,
remote unreachable, out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Very high RAG value:** a pwn-technique library (ret2libc, ret2csu, ret2dlresolve, heap notes) +
prior writeups so the agent picks the right chain fast. Consumes static understanding from `ghidra`
/ `radare2`; the captured flag feeds the CTF submission/report.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target binary/endpoint confirmed in scope before exploit development
    verify: judge
    evidence: notes/scope.txt
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
    verify: exists
    evidence: exploit.py
    on_fail: redo-skill
    required: true
  - id: result-recorded
    desc: Run marker written (flag captured, or "in progress")
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Highest-reasoning class (`effort: max`)** — a wrong step wastes a run; iterate **local-first**
  and only then fire remote.
- Keep offsets/leaks **reproducible** (cyclic patterns, scripted leaks) — don't hand-tune magic
  numbers you can't re-derive.
- Match the challenge libc exactly (use the provided libc / `pwninit`); a wrong libc breaks
  ret2libc / one_gadget offsets.
- `checksec` first — mitigations (NX/PIE/canary/RELRO) decide the whole approach.
- A run without a flag yet must still write `summary.txt` ("in progress") so "ran but empty" ≠
  "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/pwntools/<timestamp>/` (git-ignored).
