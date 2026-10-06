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
effort: medium
context: inline
agent:
category: ad-network
domain: ad
---

# netexec — network/AD swiss-army knife (nxc)

Shared contract: see AGENTS.md.

## Goal
Authenticate and enumerate across SMB/WinRM/LDAP/MSSQL/RDP — spray credentials safely, enumerate
shares/users/RIDs, run AD modules (LAPS, GPP, kerberoast), confirm access, feeding `impacket`/BloodHound.

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. **Read the lockout policy first** (threshold/observation window) so spraying can't lock accounts.
2. **Authenticate (null/guest first):** `nxc smb "$TARGETS" -u '' -p '' --log "$RUN/run.log"`, then `-u guest -p ''`, then with creds `-u <user> -p <pass>`. Log everything to the run dir.
3. **Enumerate.** `--shares --users --rid-brute` to map access and pull users/RIDs. Record readable shares, usernames, hashes in `notes/loot.md`.
4. **Protocol pivots + modules.** Repeat across `nxc ldap|winrm|mssql` and run `-M <name>` (`gpp_password`, `laps`, `kerberoast`). Throttle sprays; use `--continue-on-success` only deliberately.
5. **Loot + marker + hand-off.** Copy the nxc loot DB (`cp -a "$HOME/.nxc/." "$RUN/nxc-db/"`), write a run marker (`no valid access confirmed` if none), then write `run.json`. Feed creds/hashes to `impacket`/BloodHound.

## Modern tooling & alternatives
`netexec` (`nxc`) is the maintained fork — use it over the retired `crackmapexec`. It also collects for
BloodHound (`nxc --bloodhound`); pairs with `impacket` and `hashcat` for cracking recovered hashes.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); lockout policy checked before any spray
    verify: judge
    evidence: ../../scope.txt
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
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: lockout-safe
    desc: Spraying throttled; --continue-on-success only deliberate; no account lockouts caused
    verify: judge
    evidence: ../../scope.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Account-lockout risk on spraying** — check the policy, throttle, use `--continue-on-success` only deliberately; `lockout-safe` fails hard (`on_fail: fail`).
- Always try **null / guest** before using credentials; use `netexec`, not the retired `crackmapexec`.
- Loot persists in `~/.nxc/` — copy it into the run dir. A run that confirms nothing still writes `findings.md` + `notes/loot.md`.
