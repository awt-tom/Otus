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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes" "$RUN/loot"`); scope inherited from `out/<engagement>/scope.txt`. Parse `user[:password]` + optional keyfile. **Transport:** the local shell has no TTY, so SSH runs **one command per call** — creds via `sshpass` (password) or `-i <keyfile>` (key), host-key prompts suppressed, wrong password fails fast, every call `timeout`-wrapped; never a bare interactive `ssh` shell or `expect`. Record the channel in `notes/transport.txt`.
2. **Attempt the login (one shot)** with `SSH_COMMON="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o NumberOfPasswordPrompts=1"` — key: `timeout 30 ssh -i "$KEYFILE" -o BatchMode=yes $SSH_COMMON "$USER@$TARGET" 'id; hostname'`; password: `timeout 30 sshpass -p "$PASS" ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no $SSH_COMMON "$USER@$TARGET" 'id; hostname'`. Tee the full transcript (success or rejection) to `loot/ssh_login.txt`.
3. **Result marker + proof.** If `loot/ssh_login.txt` shows `uid=`, write `LOGIN-OK $USER@$TARGET` to `notes/result.txt` and copy it to `loot/proof.txt`; else `LOGIN-FAILED $USER@$TARGET (auth rejected)`.
4. **On success only — light read-only enum + user flag**, each its own one-shot `timeout`-bounded SSH call: `id; whoami; hostname; uname -a; sudo -n -l; ls -la ~` → `notes/enum.txt`; `cat ~/user.txt` (or `find / -maxdepth 4 -name user.txt`) → `loot/user_flag.txt`. Nothing is changed on the target.
5. **Summary + run record.** Write `findings.md` (VALID + foothold, or credential REJECTED / no state change) and `run.json` on every terminal outcome.

## Modern tooling & alternatives
A single credentialed login via `sshpass -p` (password) or `ssh -i <key> -o BatchMode=yes` (key) is the
standard foothold test — no `expect`, no interactive shell. For **many** creds use **`hydra`**; for
SMB/WinRM across a subnet use **`netexec`**; for Windows tickets/hashes use **`impacket`**. Escalate with **`privesc-root`** / **`linpeas`**.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); credential authorized for this target
    verify: judge
    evidence: ../../scope.txt
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
- **A rejected credential is a valid, complete outcome** (write the `LOGIN-FAILED` marker + `findings.md`); **read-only foothold** — no state change, owes no cleanup; the user flag/secret live only in `loot/` and the reporter redacts them.
