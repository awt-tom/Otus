---
name: ssh-foothold
description: >
  Use when validating a SUPPLIED SSH credential (password or private key) against a confirmed,
  authorized target and, on success, landing an initial read-only foothold — a one-shot
  `id`/`hostname` proof, light non-destructive enumeration, and the user flag if present. A single
  credential test, NOT a brute-force spray (use hydra for online brute, netexec for SMB/WinRM). Runs
  non-interactively (no expect, no held shell).
arguments: "target user[:password] [keyfile]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: access
domain: host
---

# ssh-foothold — validate a supplied SSH credential and land an initial foothold

Shared contract: see AGENTS.md.

## Goal
Prove non-interactively whether one supplied SSH credential is valid on an authorized target and
capture raw `id`/`hostname` proof and only goal-relevant read-only context. A failed login is error.

## Steps
1. Parse ONE supplied credential, verified ssh/sshpass identity and endpoint/port. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ssh-foothold --target "$TARGET" --profile single-credential --coverage-set 'One supplied credential and identity proof')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, 30-second login cap and <=60-second initial task; record channel/key-trust method, not secrets, in notes/transport.txt.
2. Key example: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 30 --grace 5 -- ssh -i "$KEYFILE" -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$RUN/notes/known_hosts" "$USER@$TARGET" 'id && hostname' > "$RUN/loot/ssh_login.txt"`. Prefer supplied pinned host keys; preserve trust on later calls. Password alternative uses `SSHPASS="$PASS"` on the helper process and `sshpass -e ssh`, with password auth only and `NumberOfPasswordPrompts=1`; same connection/trust/cap, no interactive prompt.
3. Derive LOGIN-OK only from actual identity/hostname output and zero exit; copy raw proof to loot/proof.txt, never just the marker. Otherwise record LOGIN-FAILED with the actual auth/connection/tool reason and error handback, no retry or SSH-255 reclassification. Secrets stay private.
4. After proved access and only within remaining allocation, one 30-second helper-wrapped read-only call for `uname -a; pwd; ls -la ~` is sufficient context. Read a known user.txt only for an HTB/CTF flag objective; no whole-filesystem search, mandatory flag or bundled `sudo -n -l` whose denial hides successful access.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other credentials and broad host enumeration' --item 'scope-confirmed=ok:../../scope.json' --item 'transport-recorded=ok:notes/transport.txt' --item 'login-result=ok:notes/result.txt' --target-state unchanged --cleanup not-needed`; complete only the proved declared login task; missing proof is partial, failed command error. Return actual access refs to coordinator, never chain privesc.

## Modern tooling & alternatives
A single credentialed login via `sshpass -p` (password) or `ssh -i <key> -o BatchMode=yes` (key) is the
standard foothold test — no `expect`, no interactive shell. For **many** creds use **`hydra`**; for
SMB/WinRM across a subnet use **`netexec`**; for Windows tickets/hashes use **`impacket`**. Escalate with **`privesc-root`** / **`linpeas`**.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization, endpoint, and supplied credential use checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: transport-recorded
    desc: SSH transport (user@target, password/key method) recorded so the channel is auditable
    verify: nonempty
    evidence: notes/transport.txt
    on_fail: redo-part
    required: true
  - id: login-result
    desc: Result matches actual command events and raw auth/connection/identity outcome
    verify: judge
    evidence: notes/result.txt
    on_fail: redo-part
    required: true
  - id: foothold-proof
    desc: On a successful login, the id/hostname foothold proof is captured (absent on a rejected credential)
    verify: judge
    evidence: loot/proof.txt
    on_fail: fail
    required: false
```

## Notes / pitfalls
- A single failed credential can affect lockout counters; no attempt budget or safety guarantee is inferred.
- Preserve host-key verification and bounded noninteractive proof; no held shell, expect or hidden failures.
- Rejected credentials leave LOGIN-FAILED and an error handback, never a retry. Read-only proof owes no cleanup; secrets stay private and are redacted by the reporter.
