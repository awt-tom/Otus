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
1. Put every expanded TARGETS endpoint into plain `HOSTS`. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill netexec)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. Record lockout thresholds/window and actual outcome in `notes/lockout.txt`.
2. **Authenticate:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" -- nxc smb "$TARGETS" -u '' -p '' --log "$RUN/evidence/nxc.log"`, then original `-u guest -p ''` / credential variants through the same helper. The tool-specific log is separate from raw run.log.
3. **Enumerate.** `--shares --users --rid-brute` to map access and pull users/RIDs. Record readable shares, usernames, hashes in `notes/loot.md`.
4. **Protocol pivots + modules.** Repeat across `nxc ldap|winrm|mssql` and run `-M <name>` (`gpp_password`, `laps`, `kerberoast`). Throttle sprays; use `--continue-on-success` only deliberately.
5. Every enumeration/module/protocol call uses the checked helper; copy only THIS run's relevant DB/loot to `nxc-db/`/`loot/`, not unrelated historical targets. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'auth-enumerated=ok:run.log' --item 'results-recorded=ok:findings.md' --item 'lockout-safe=ok:notes/lockout.txt'`; add secret-free verified findings and actual cleanup fields, or `no valid access confirmed`.

## Modern tooling & alternatives
`netexec` (`nxc`) is the maintained fork — use it over the retired `crackmapexec`. It also collects for
BloodHound (`nxc --bloodhound`); pairs with `impacket` and `hashcat` for cracking recovered hashes.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and every authentication/pivot target checked
    verify: judge
    evidence: ../../scope.json
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
    evidence: notes/lockout.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Account-lockout risk on spraying** — check the policy, throttle, use `--continue-on-success` only deliberately; `lockout-safe` fails hard (`on_fail: fail`).
- Always try **null / guest** before using credentials; use `netexec`, not the retired `crackmapexec`.
- Copy only this invocation's relevant cached artifacts; never import unrelated targets. No access still finishes with notes/loot.md and matching summary.
