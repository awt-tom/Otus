---
name: privesc-root
description: >
  Use when escalating an authorized foothold to root and proving it — run the chosen privesc vector
  (SUID/sudo/cron/capability/kernel or a known-vulnerable local service), capture a non-destructive
  uid=0 transcript as proof, and grab /root/root.txt. Consumes a vector from linpeas/searchsploit or a
  foothold from metasploit/web-exploit. Not for enumeration (linpeas) or framework exploitation (metasploit).
arguments: "target [vector]"
model: inherit
effort: medium
context: inline
agent:
category: privesc-creds
domain: host
---

# privesc-root — escalate to root, prove it, capture the flag

Shared contract: see AGENTS.md.

## Goal
Turn a confirmed vector into verified root on an authorized host: execute the escalation, capture a
non-destructive transcript proving `uid=0(root)`, and record the root flag — certifiable evidence, not a self-report.

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes" "$RUN/loot"`); scope inherited from `out/<engagement>/scope.txt`. **Transport:** the local shell holds no session on the target — run every target-side command through an explicit foothold channel (`ssh user@target '<cmd>'`, a webshell/RCE one-shot, or `tmux send-keys`/`capture-pane`) and tee output back locally. Record it in `notes/transport.txt`.
2. **Enumerate + identify the vector.** Run `linpeas` plus, in the foothold, `uname -a; sudo -l; find / -perm -4000 -type f 2>/dev/null; getcap -r / 2>/dev/null` → `notes/enum.txt`; capture the vulnerable service's exact version; `searchsploit <service/version>` (local) maps version→exploit. Record the chosen vector + exact version/ref in `notes/version.txt`.
3. **Escalate (least-destructive).** Run the chosen vector through the transport, teeing the **full** transcript (incl. failed attempts, which corroborate the working path) to `loot/root-shell.log`.
4. **Prove root (non-destructive).** In the root context run read-only checks `id; whoami; hostname` → `loot/root-proof.txt` — this transcript is the certifiable proof and must show `uid=0`.
5. **Flag + summary + run record.** `cat /root/root.txt` → `notes/root-flag.txt` (marker if absent); write `findings.md` (root proven / not achieved) and `run.json`.

## Modern tooling & alternatives
Enumerate first with `linpeas`/`pspy`; map findings to abuse via **GTFOBins / LOLBAS** and kernel/OS
exploits via `linux-exploit-suggester` / `wesng`. Service CVEs from `searchsploit`/ExploitDB — a single
hand-written PoC is often cleaner than a framework. Prefer least-destructive; kernel exploits (can crash the host) are a last resort.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); foothold host authorized
    verify: judge
    evidence: ../../scope.txt
    on_fail: fail
    required: true
  - id: transport-recorded
    desc: Foothold transport (ssh / webshell-RCE / reverse-shell) recorded so the channel to the target is auditable
    verify: nonempty
    evidence: notes/transport.txt
    on_fail: redo-part
    required: true
  - id: vector-identified
    desc: Privesc enumeration captured and the chosen vector + exact vulnerable version/reference recorded
    verify: judge
    evidence: notes/version.txt
    on_fail: redo-part
    required: true
  - id: root-proof
    desc: Captured transcript proves root (uid=0) non-destructively
    verify: contains:uid=0
    evidence: loot/root-proof.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Local shell is one-shot** — run every target-side command through the recorded transport and tee output back; a command run locally proves nothing about the target.
- **Least-destructive proof** — `id`/`whoami`/`hostname` + read the flag; don't modify system files or add users. Keep failed attempts (they corroborate the vector).
- **Record the exact vulnerable version** (`vector-identified`); "it worked" without the version isn't certifiable. Kernel exploits can crash the host — verify version match, last resort.
- **Cleanup:** if you planted any artifact, verify removal to `loot/cleanup_verify.txt` per AGENTS.md § cleanup before declaring clean; on an aborted run, record owed cleanup in `findings.md`.
