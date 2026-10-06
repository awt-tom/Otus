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
context: inline
agent:
category: access
domain: host
---

# ssh-foothold — validate a supplied SSH credential and land an initial foothold

Shared contract: see AGENTS.md.

## Goal
Prove non-interactively whether one supplied SSH credential is valid on an authorized target and
capture the outcome — on success `id`/`hostname` proof + read-only enum + user flag; a proven-*invalid* credential is also a complete run.

## Steps
1. Parse supplied credentials. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ssh-foothold --target "$TARGET")"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Record the one-shot channel, not the password, in `notes/transport.txt`.
2. Set `SSH_COMMON="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o NumberOfPasswordPrompts=1"`. Wrap either original key `timeout 30 ssh -i "$KEYFILE" -o BatchMode=yes $SSH_COMMON "$USER@$TARGET" 'id; hostname'` or password `timeout 30 sshpass -p "$PASS" ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no $SSH_COMMON "$USER@$TARGET" 'id; hostname'` with `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --`; redirect its output to `loot/ssh_login.txt`. On nonzero, record LOGIN-FAILED and enrich the error handback; no retry.
3. **Result marker + proof.** If `loot/ssh_login.txt` shows `uid=`, write `LOGIN-OK $USER@$TARGET` to `notes/result.txt` and copy it to `loot/proof.txt`; else `LOGIN-FAILED $USER@$TARGET (auth rejected)`.
4. **On success only:** wrap each timeout-bounded SSH enum/flag call with the same helper and target. `id; whoami; hostname; uname -a; sudo -n -l; ls -la ~` goes to `notes/enum.txt`; `cat ~/user.txt` (or `find / -maxdepth 4 -name user.txt`) goes to `loot/user_flag.txt`. No target changes.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'transport-recorded=ok:notes/transport.txt' --item 'login-result=ok:notes/result.txt' --target-state unchanged --cleanup not-needed`; STATUS is complete on proven login, error on rejected/failed login. Keep secrets out of summaries.

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
    desc: Result marker written from the captured transcript so "ran, credential invalid" is distinguishable from "didn't run"
    verify: contains:(LOGIN-OK|LOGIN-FAILED)
    evidence: notes/result.txt
    on_fail: redo-part
    required: true
  - id: foothold-proof
    desc: On a successful login, the id/hostname foothold proof is captured (absent on a rejected credential)
    verify: contains:(uid=)
    evidence: loot/proof.txt
    on_fail: redo-skill
    required: false
```

## Notes / pitfalls
- **Single credential test, not brute-force** — one credential; for spraying use `hydra`. `NumberOfPasswordPrompts=1` makes a wrong password fail after one prompt (avoids lockout + the re-prompt loop an `expect` script causes).
- **Always non-interactive** — `sshpass`/`BatchMode=yes`, `StrictHostKeyChecking=no`, `ConnectTimeout`, wrapping `timeout`; never a bare `ssh` shell or `expect`. A `timeout` stall is a tool failure, not a guardrail.
- Rejected credentials leave LOGIN-FAILED and an error handback, never a retry. Read-only proof owes no cleanup; secrets stay private and are redacted by the reporter.
