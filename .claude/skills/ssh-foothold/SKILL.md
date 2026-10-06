---
name: ssh-foothold
description: >
  Use when validating a SUPPLIED SSH credential (password or private key) against a confirmed,
  authorized target and, on success, landing an initial read-only foothold — a one-shot
  `id`/`hostname` proof, light non-destructive enumeration, and the user flag if present. This is a
  single credential test, NOT a brute-force spray (use hydra for online brute, netexec for SMB/WinRM,
  privesc-root to escalate a foothold to root). All SSH runs non-interactively (no expect, no held
  shell).
arguments: "target user[:password] [keyfile]"
model: inherit
effort: medium
context: inline
agent:
---

# ssh-foothold — validate a supplied SSH credential and land an initial foothold

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Confirm the target is in scope and that you are permitted to log in with the supplied credential before running anything. Single credential test only — never brute-force. Abort if the target is not confirmed in scope.

## Goal (desired outcome)
Prove whether one supplied SSH credential is valid on an authorized target, **non-interactively**, and
capture the outcome as reviewable evidence: on success, a one-shot `id`/`hostname` proof plus light
read-only enumeration and the user flag if present; on failure, the genuine auth-rejection transcript.
Either outcome is a complete, verifiable run — a correctly-proven *invalid* credential is a success of
this skill, not a failure.

## Steps
> **Foothold transport (read first).** The operator's Claude Code Bash tool runs each command in a
> **fresh, one-shot LOCAL shell with no TTY** — it cannot answer a password prompt and holds **no**
> live shell on the target between calls. So SSH is driven **non-interactively, one command per call**:
> the credential is fed with `sshpass` (password) or `-i <keyfile>` (key), host-key prompts are
> suppressed, a wrong password **fails fast** (`NumberOfPasswordPrompts=1`) instead of re-prompting,
> and every call is wrapped in `timeout`. **Never** open a bare interactive `ssh user@host` shell and
> **never** use an `expect` script — both hang the run. Record the chosen channel in
> `notes/transport.txt`. If a foothold must persist across steps, hand off to a detached `tmux`
> session (`send-keys` / `capture-pane`), never a foreground shell.

1. **Precondition / scope / input.** Confirm scope and parse the supplied credential. Anchor a
   timestamped run directory to the repo root (never write under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_ssh_foothold="${OTUS_RUN_DIR:-$ROOT/out/${ENGAGEMENT:?engagement slug required}/ssh-foothold/$(date -u +%Y%m%dT%H%M%SZ)}"
   RUN="$OTUS_RUN_ssh_foothold"
   started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
   mkdir -p "$RUN/notes" "$RUN/loot"
   TARGET="${1:?target required}"; USERSPEC="${2:?user[:password] required}"; KEYFILE="${3:-}"
   USER="${USERSPEC%%:*}"; PASS="${USERSPEC#*:}"; [ "$PASS" = "$USERSPEC" ] && PASS=""
   echo "target $TARGET user $USER confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   echo "transport=ssh method=$( [ -n "$KEYFILE" ] && echo key || echo password ) user=$USER@$TARGET" > "$RUN/notes/transport.txt"
   : > "$RUN/run.log"
   ```
2. **Attempt the login non-interactively (one shot).** Use the key path when a keyfile is given, else
   the password path via `sshpass`. Host-key checking is disabled for the lab, a wrong password fails
   after **one** prompt, and the whole thing is `timeout`-bounded so it can never hang. Tee the **full**
   transcript (success or rejection) to `loot/ssh_login.txt`:
   ```bash
   SSH_COMMON="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o NumberOfPasswordPrompts=1"
   if [ -n "$KEYFILE" ]; then
     timeout 30 ssh -i "$KEYFILE" -o BatchMode=yes $SSH_COMMON "$USER@$TARGET" \
       'id; hostname' 2>&1 | tee "$RUN/loot/ssh_login.txt"
   else
     timeout 30 sshpass -p "$PASS" ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no \
       $SSH_COMMON "$USER@$TARGET" 'id; hostname' 2>&1 | tee "$RUN/loot/ssh_login.txt"
   fi
   ```
3. **Record the result marker** so "ran, credential invalid" ≠ "didn't run", and on success capture
   the foothold proof:
   ```bash
   if grep -q 'uid=' "$RUN/loot/ssh_login.txt"; then
     echo "LOGIN-OK $USER@$TARGET" > "$RUN/notes/result.txt"
     cp "$RUN/loot/ssh_login.txt" "$RUN/loot/proof.txt"
   else
     echo "LOGIN-FAILED $USER@$TARGET (auth rejected — see loot/ssh_login.txt)" > "$RUN/notes/result.txt"
   fi
   ```
4. **On success only — light read-only enumeration + user flag.** Each command is its own one-shot,
   `timeout`-bounded SSH call (reuse the working credential form from step 2); nothing is changed on
   the target:
   ```bash
   # replace <SSH> with the exact working invocation from step 2 (key or sshpass form), minus the final 'cmd'
   if grep -q '^LOGIN-OK' "$RUN/notes/result.txt"; then
     timeout 30 <SSH> "$USER@$TARGET" 'id; whoami; hostname; uname -a; sudo -n -l 2>/dev/null; ls -la ~ 2>/dev/null' \
       2>&1 | tee "$RUN/notes/enum.txt"
     timeout 20 <SSH> "$USER@$TARGET" 'cat ~/user.txt 2>/dev/null || find / -maxdepth 4 -name user.txt 2>/dev/null | head -1 | xargs -r cat' \
       2>&1 | tee "$RUN/loot/user_flag.txt"
   fi
   ```
5. **Summary + run record.** Always write `findings.md` and `run.json` into `$RUN/` (schema in Output
   formats) on every terminal outcome:
   ```bash
   if grep -q '^LOGIN-OK' "$RUN/notes/result.txt"; then
    echo "ssh-foothold: $USER@$TARGET VALID — foothold obtained (see loot/proof.txt); user flag in loot/user_flag.txt if present" > "$RUN/findings.md"
   else
    echo "ssh-foothold: $USER@$TARGET credential REJECTED at the SSH auth layer (see loot/ssh_login.txt). No foothold. No state change." > "$RUN/findings.md"
   fi
   ```

## Modern tooling & alternatives
A single credentialed SSH login, driven non-interactively with `sshpass -p` (password) or
`ssh -i <key> -o BatchMode=yes` (key), is the standard foothold test — no `expect`, no interactive
shell. For **many** credentials or spraying use **`hydra`** (online brute); for SMB/WinRM/MSSQL
credential checks across a subnet use **`netexec`**; for Windows auth via tickets/hashes use
**`impacket`**. Once a foothold is obtained, escalate with **`privesc-root`** / **`linpeas`**.

## Output formats
Written only under the anchored run dir (`out/<engagement>/ssh-foothold/<timestamp>/`, git-ignored):
- `loot/ssh_login.txt` — full login transcript (success or rejection).
- `loot/proof.txt` — on success, the `id`/`hostname` foothold proof.
- `notes/result.txt` — `LOGIN-OK` / `LOGIN-FAILED` marker.
- `notes/transport.txt`, `notes/scope.txt`, `notes/enum.txt` (on success), `loot/user_flag.txt`
  (on success), `findings.md`, `run.log`, and a run record `$RUN/run.json`:
```json
{
  "skill": "ssh-foothold",
  "engagement": "<engagement slug>",
  "target": "<target>",
  "run_dir": "out/<engagement>/ssh-foothold/<timestamp>",
  "started": "<started: date -u +%Y-%m-%dT%H:%M:%SZ, ISO-8601 UTC>",
  "finished": "<finished: date -u at finish; must be >= started>",
  "status": "complete",
  "summary": "<one line>",
  "evidence": ["findings.md"],
  "items": {
    "scope-confirmed":    { "ok": true, "evidence": "notes/scope.txt" },
    "run-log":            { "ok": true, "evidence": "run.log" },
    "transport-recorded": { "ok": true, "evidence": "notes/transport.txt" },
    "login-attempt":      { "ok": true, "evidence": "loot/ssh_login.txt" },
    "login-result":       { "ok": true, "evidence": "notes/result.txt" },
    "foothold-proof":     { "ok": true, "evidence": "loot/proof.txt" },
    "run-record":         { "ok": true, "evidence": "run.json" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. A valid credential that logs in and a correctly-rejected
credential are both `complete` (the skill ran and proved the outcome). Set `status: error` only on a
real failure to execute — target unreachable, `sshpass` missing, timeout/hang, or out of scope — with
a human-readable line in `errors[]`. A connection stall that trips `timeout` is a tool failure
(`status: error`), **not** a guardrail.

## RAG / shared data / cross-skill
Credentials come from prior phases (nmap/service notes, a web foothold, `hashcat` cracks, an AD dump)
and a per-engagement credential store. A confirmed SSH foothold feeds privilege escalation
(`privesc-root`, `linpeas`) and AD post-ex (`impacket`, `netexec`); the user flag and host facts feed
reporting. For spraying many creds, hand off to `hydra`.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target + credential confirmed in scope before any login attempt
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: run-log
    desc: Run log initialized and written to the run directory
    verify: exists
    evidence: run.log
    on_fail: redo-part
    required: true
  - id: transport-recorded
    desc: SSH transport (user@target, password/key method) recorded so the channel is auditable
    verify: nonempty
    evidence: notes/transport.txt
    on_fail: redo-part
    required: true
  - id: login-attempt
    desc: Full SSH login transcript captured (success or auth rejection)
    verify: nonempty
    evidence: loot/ssh_login.txt
    on_fail: redo-part
    required: true
  - id: login-result
    desc: Result marker written so "ran, credential invalid" is distinguishable from "didn't run"
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
  - id: run-record
    desc: Run record run.json written for the run
    verify: exists
    evidence: run.json
    on_fail: redo-part
    required: true
```

## Notes / pitfalls
- **Scope first** — `scope-confirmed` fails hard (`on_fail: fail`); never attempt a login against an
  unconfirmed target or with a credential you are not authorized to use.
- **Single credential test, not brute-force** — one credential, throttled; for spraying use `hydra`.
  `NumberOfPasswordPrompts=1` ensures a wrong password fails after one prompt (avoids lockout and the
  re-prompt loop an `expect` script can cause).
- **Always non-interactive** — `sshpass -p` / `ssh -i … -o BatchMode=yes`, `StrictHostKeyChecking=no`,
  `ConnectTimeout`, and a wrapping `timeout`. **Never** a bare interactive `ssh` shell or an `expect`
  script — both hang the one-shot operator shell (see CLAUDE.md § "Non-interactive execution").
- **Local shell is one-shot** — no SSH session survives between calls; run each on-target command as
  its own `ssh user@target '<cmd>'` and tee output into the local run dir. A command run locally by
  mistake proves nothing about the target.
- **Rejected credential is a valid outcome** — write the `LOGIN-FAILED` marker and `findings.md` so a
  genuine auth rejection is recorded as a completed run, not a half-run.
- **Flag/secret hygiene** — the user flag and any secret live only in `loot/` evidence files; the
  reporter redacts them (presence + location only) in the report body.
- **Read-only foothold** — this skill only reads (enumeration, flag). It makes no state change, so a
  clean run owes no `loot/cleanup_verify.txt`; escalation that changes state is `privesc-root`'s job.
- **A stall is a tool failure, not a guardrail** — if a call trips `timeout`, set `run.json`
  `status: error` with the reason and hand back; do not retry interactively.
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `run.json` (`status: error`, block type + request id in `errors[]`) and `findings.md` recording the stop,
  then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/<engagement>/ssh-foothold/<timestamp>/` (git-ignored).
