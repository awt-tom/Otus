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
context: fork
agent: vuln-hunter
background: false
category: privesc-creds
domain: host
---

# privesc-root — escalate to root, prove it, capture the flag

Shared contract: see AGENTS.md.

## Goal
Test one confirmed privilege vector and capture real elevated identity/access proof.
Flags belong only to an HTB/CTF objective; missing proof is a goal gap, not a replay trigger.

## Steps
1. Reuse ONE reviewed vector and proved foothold transport. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill privesc-root --target "$TARGET" --profile selected-vector --coverage-set 'One privilege vector and elevated identity proof')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with known identity, hypothesis, <=120-second command caps/finite total allocation and minimum proof; record transport in notes/transport.txt.
2. Cheapest specific prerequisite check only; no re-running linpeas, filesystem-wide finds or default kernel exploits. Record exact rule/path/permission/version and matched/unmet prerequisites in notes/version.txt. If selected, `sudo -n -l` is its own bounded one-shot; denial is recorded error, never an interactive retry or masked success. No applicable vector -> partial, no firing.
3. Escalation/proof CLI: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 120 --grace 5 -- <verified one-shot transport argv>` with remote-native bounds fitting remaining allocation. Save the real transcript; hard failure stops, no replay. Capture `id && whoami && hostname` in the established elevated context to loot/root-proof.txt without rerunning an actionful escalation. Target proof is not a local operator `id` or a fabricated marker.
4. Read the known /root/root.txt only for a flag objective and actual established access; store private loot/root-flag.txt. Assessment needs minimum proved privilege/impact, not the flag. Record exact mutations and positive cleanup absence checks, or owed/unknown remote state after failure.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other privilege vectors and post-exploitation' --item 'scope-confirmed=ok:../../scope.json' --item 'transport-recorded=ok:notes/transport.txt' --item 'vector-identified=ok:notes/version.txt'`; add root-proof/finding only for real identity evidence, otherwise partial/error with goal gap and actual state/artifacts/cleanup. Return to coordinator, never start another skill.

## Modern tooling & alternatives
Reuse reviewed GTFOBins/LOLBAS/CVE prerequisites; kernel exploits are an exceptional last resort.
Do not repeat broad enumeration merely because a root flag has not yet been reached.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and foothold/proof host checked
    verify: judge
    evidence: ../../scope.json
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
    desc: Every claimed elevation has actual target identity/access proof; absent proof is partial
    verify: judge
    evidence: loot/root-proof.txt
    on_fail: fail
    required: false
```

## Notes / pitfalls
- **Local shell is one-shot** — run every target-side command through the recorded transport and tee output back; a command run locally proves nothing about the target.
- **Least-destructive proof** — `id`/`whoami`/`hostname` + read the flag; don't modify system files or add users. Keep failed attempts (they corroborate the vector).
- **Record the exact vulnerable version** (`vector-identified`); "it worked" without the version isn't certifiable. Kernel exploits can crash the host — verify version match, last resort.
- **Cleanup:** if you planted any artifact, verify removal to `loot/cleanup_verify.txt` per AGENTS.md § cleanup before declaring clean; on an aborted run, record owed cleanup in `findings.md`.
