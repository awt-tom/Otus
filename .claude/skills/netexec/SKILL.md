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
context: fork
agent: vuln-hunter
background: false
category: ad-network
domain: ad
---

# netexec — network/AD swiss-army knife (nxc)

Shared contract: see AGENTS.md.

## Goal
Test one selected Windows/AD protocol and supplied identity, then only goal-relevant enumeration.
Authentication, privilege and readable-resource access are separate claims.

## Steps
1. Select a known protocol/service and ONE supplied identity; put every contacted endpoint in plain HOSTS. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill netexec --profile selected-protocol --coverage-set 'One selected protocol and supplied identity')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, binary/version, <=60-second command cap/finite task allocation and proof criterion; record known/unknown lockout allowance/prior attempts in notes/lockout.txt.
2. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" --timeout 60 --grace 5 -- nxc "$PROTOCOL" "$TARGET" -u "$USER" -p "$PASS" -t 1 --log "$RUN/evidence/nxc.log"`; verify supported protocol/flags first. No mandatory null/guest attempt before supplied credentials. Keep tool-specific logs private and unchanged; zero exit alone is not successful authentication.
3. If auth is proved and allocation remains, choose one relevant shares/users/rule query using the same checked wrapper, not combined shares/users/RID-brute or automatic protocol/module ladders. Modules, RID discovery and credential attacks need their own specific lead/allocation and known aggregate per-account policy; unknown allowance -> no spray.
4. Record actual credential validity, privilege/resource proof refs, tested/omitted hosts, native errors/skips and unknown effects in notes/results.md. Copy only this invocation's relevant cache/loot, never unrelated targets or secrets in notes. Hard failure/refusal stops; no retry on another protocol or continuation after lockout/degradation.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other identities, protocols and modules' --item 'scope-confirmed=ok:../../scope.json' --item 'auth-enumerated=ok:events.jsonl' --item 'results-recorded=ok:notes/results.md' --item 'lockout-safe=ok:notes/lockout.txt'`; include only secret-free verified findings and actual state/artifacts/cleanup. A finished selected no-access task can be complete, skipped/inconclusive partial, nonzero error. Return next-task proposal to coordinator.

## Modern tooling & alternatives
`netexec` (`nxc`) is the maintained fork — use it over the retired `crackmapexec`. It also collects for
BloodHound (`nxc --bloodhound`); pairs with `impacket` and `hashcat` for cracking recovered hashes.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and every authentication/pivot target checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: auth-enumerated
    desc: Paired events and native proof substantiate selected auth/query and actual outcomes
    verify: judge
    evidence: events.jsonl
    on_fail: fail
    required: true
  - id: results-recorded
    desc: Validity, privilege and resource claims are distinct, with real refs and honest omissions
    verify: judge
    evidence: notes/results.md
    on_fail: fail
    required: true
  - id: lockout-safe
    desc: Aggregate/per-account attempt allowance respected; actual/unknown effects disclosed
    verify: judge
    evidence: notes/lockout.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Account-lockout risk on spraying** — check the policy, throttle, use `--continue-on-success` only deliberately; `lockout-safe` fails hard (`on_fail: fail`).
- Null/guest is a selected hypothesis, never a prerequisite; use maintained `nxc`.
- Target is one checked endpoint, not an unchecked CIDR/range hidden in TARGETS.
