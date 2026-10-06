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
context: inline
agent:
category: re-forensics
domain: binary
---

# pwntools — exploit development framework (Python)

Shared contract: see AGENTS.md.

## Goal
Build a working, reproducible exploit for a pwn challenge — model the binary's I/O, defeat its
mitigations, deliver a payload — tested locally first, then fired at the remote to capture the flag.

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Record mitigations: `checksec "$BIN" 2>&1 | tee "$RUN/notes/checksec.txt"` (RELRO/NX/PIE/canary dictate the technique).
2. **Model I/O** — one script targets local + remote via `args` (save as `$RUN/exploit.py`): after `from pwn import *`, `io = remote(args.HOST, int(args.PORT)) if args.HOST else process(args.BIN or "./chall")`.
3. **Find the offset / leak.** `cyclic`/`cyclic_find` for the overflow offset; leak GOT/libc and defeat mitigations (canary, PIE, ASLR). Keep offsets/leaks reproducible, noted in `notes/`.
4. **Build the payload** with `ROP(exe)`, `shellcraft`, `p64()`/`flat()` — ret2libc / ret2csu / ret2dlresolve / format-string per challenge. Debug with `gdb.attach(io)` (pwndbg/GEF); `ROPgadget`/`ropper` for gadgets, `one_gadget` for libc shells.
5. **Local → remote + capture + run record.** Get a shell/flag locally (`python3 "$RUN/exploit.py" BIN="$BIN"`), then flip to remote `HOST=… PORT=…`; grep the flag to `$RUN/flag.txt`. Write a run marker (`in progress` if no flag), then `run.json`.

## Modern tooling & alternatives
`pwntools` + `gdb` with `pwndbg`/`GEF`; `ROPgadget`/`ropper` for gadgets; `one_gadget` for libc one-shot
shells; `angr` for symbolic execution; `checksec` for mitigations. Pair with `ghidra`/`radare2` for the static side.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); binary/endpoint authorized
    verify: judge
    evidence: ../../scope.txt
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
    evidence: findings.md
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Highest-reasoning class** — a wrong step wastes a run; iterate **local-first**, only then fire remote.
- Keep offsets/leaks **reproducible** (cyclic patterns, scripted leaks) — don't hand-tune magic numbers you can't re-derive.
- Match the challenge libc exactly (provided libc / `pwninit`); a wrong libc breaks ret2libc / one_gadget offsets. `checksec` first — mitigations decide the whole approach.
- A run without a flag yet must still write `findings.md` ("in progress").
