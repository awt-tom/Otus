---
name: netexec
description: >
  Use when authenticating to and enumerating Windows/AD services at scale with netexec (nxc,
  the maintained CrackMapExec fork) — SMB/WinRM/LDAP/MSSQL/RDP: spray creds, enumerate
  shares/users, RID-brute, run modules (gpp_password, laps, kerberoast), confirm access.
  Feeds impacket/BloodHound. Not for web testing (burpsuite) or single-host exploits
  (metasploit). Account-lockout risk — check policy before spraying.
arguments: "targets [-u user] [-p pass] [protocol]"
model: inherit
effort: high
context: inline
agent:
---

# netexec — network/AD swiss-army knife (nxc)

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Confirm the target hosts/domain are in scope **and check the account-lockout policy before any credential spray** — a spray that locks out accounts is destructive. Abort if the targets are not confirmed in scope.

## Goal (desired outcome)
Authenticate and enumerate/act across SMB/WinRM/LDAP/MSSQL/RDP — spray credentials safely,
enumerate shares/users/RIDs, run AD modules (LAPS, GPP, kerberoast), and confirm access — feeding
loot (creds/hashes) to `impacket` and BloodHound, with the full transcript captured.

## Steps
1. **Precondition / scope / lockout check.** Confirm targets are in scope and **read the lockout
   policy first** (threshold/observation window) so spraying can't lock accounts. Anchor a
   timestamped run directory to the repo root (never write under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/netexec/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   TARGETS="${1:?targets (host/CIDR/file) required}"
   echo "targets $TARGETS confirmed in scope; lockout policy checked: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/loot.md"
   ```
2. **Authenticate (null/guest first).** Start unauthenticated, logging to the run dir:
   ```bash
   nxc smb "$TARGETS" -u '' -p '' --log "$RUN/run.log"        # null session
   nxc smb "$TARGETS" -u guest -p '' --log "$RUN/run.log"     # guest
   # then, with creds: nxc smb "$TARGETS" -u <user> -p <pass> --log "$RUN/run.log"
   ```
3. **Enumerate.** `--shares --users --rid-brute` to map access and pull users/RIDs. Record anything
   useful (readable shares, usernames, hashes) in `notes/loot.md`.
4. **Protocol pivots + modules.** Repeat across protocols (`nxc ldap`, `nxc winrm`, `nxc mssql`) and
   run modules with `-M <name>` (e.g. `gpp_password`, `laps`, `kerberoast`). Throttle sprays; use
   `--continue-on-success` only deliberately. Note confirmed access/creds in `notes/loot.md`.
5. **Loot + marker + hand-off.** Copy the nxc loot DB into the run dir, then write a run marker so
   "ran but nothing" ≠ "didn't run":
   ```bash
   cp -a "$HOME/.nxc/." "$RUN/nxc-db/" 2>/dev/null || true
   if grep -qiE '\(Pwn3d!\)|\[\+\]' "$RUN/run.log"; then
     echo "netexec: valid access/creds found (see run.log + notes/loot.md)" > "$RUN/summary.txt"
   else
     echo "no valid access confirmed" > "$RUN/summary.txt"; echo "none" >> "$RUN/notes/loot.md"
   fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats). Feed creds/hashes
   to `impacket` / BloodHound.

## Modern tooling & alternatives
`netexec` (`nxc`) is the maintained fork — use it over the retired `crackmapexec`. It also collects
for BloodHound (`nxc --bloodhound`). Pairs with `impacket` for protocol-level actions and `hashcat`
for cracking recovered hashes.

## Output formats
Colorized CLI; persistent loot DB under `~/.nxc/` (copied into `$RUN/nxc-db/`); `--log` mirrors
output to `$RUN/run.log`. This skill also writes `$RUN/notes/loot.md` (creds/shares/hashes),
`$RUN/summary.txt` (run marker), and a run record `$RUN/_run.json`:
```json
{
  "skill": "netexec",
  "target": "<targets>",
  "run_dir": "out/netexec/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "auth-enumerated":  { "attempted": true, "ok": true, "evidence": "run.log", "exit": 0 },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "lockout-safe":     { "attempted": true, "ok": true, "evidence": "notes/scope.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (nxc missing, targets unreachable, out of
scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Feeds and is fed by BloodHound + `impacket`; the recovered-credential store is **shared across the
AD skills**. **Very high RAG value:** a WADCOMS / AD-attack map ("I have X → do Y") and module
cheat-sheet. Hashes recovered here feed `hashcat`; cracked creds loop back into `netexec` as a new
identity.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Targets confirmed in scope AND lockout policy checked before any spray
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: auth-enumerated
    desc: Authentication/enumeration executed and logged (null/guest first)
    verify: nonempty
    evidence: run.log
    on_fail: redo-skill
    required: true
  - id: results-recorded
    desc: Run marker written (even when no access/creds found)
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: lockout-safe
    desc: Spraying throttled; --continue-on-success only deliberate; no account lockouts caused
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Account-lockout risk on spraying** — check the policy, throttle, and use
  `--continue-on-success` only deliberately; `lockout-safe` fails hard (`on_fail: fail`).
- Always try **null / guest** before using credentials.
- Use `netexec`, not the retired `crackmapexec`.
- Loot persists in `~/.nxc/` across runs — copy it into the run dir for self-contained evidence.
- A run that confirms nothing must still write `summary.txt` ("no valid access confirmed") and
  `notes/loot.md` so "ran but empty" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/netexec/<timestamp>/` (git-ignored).
