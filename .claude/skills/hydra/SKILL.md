---
name: hydra
description: >
  Use when brute-forcing or password-spraying an online login service with hydra — ssh, ftp,
  rdp, smb, and HTTP login forms (http-post-form / http-get-form) — using a user/password list
  to find valid credentials. Consumes wordlists; feeds valid creds to login/AD/web skills. Not
  for offline hash cracking (use hashcat) and not for web content discovery (use ffuf).
arguments: "target service [-L userlist] [-P passlist] [form_spec]"
model: inherit
effort: medium
context: inline
agent:
category: access
domain: network
---

# hydra — online login brute-forcing

Shared contract: see AGENTS.md.

## Goal
Find valid credentials on an online login service (ssh/ftp/rdp/smb/HTTP form) by testing a
user/password list — throttled to avoid lockouts — and record any valid logins for auth/web skills.

## Steps
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill hydra --target "$TARGET")"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Record lockout policy and actual outcome in `notes/lockout.txt`; use small targeted lists.
2. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" -- hydra -L users.txt -P pass.txt -t 4 -f -o "$RUN/found.txt" -b json "$TARGET" "$SERVICE"` (`-l`/`-p` single value, `-s` port, `-f` first hit, `-t` throttle).
3. HTTP form alternative: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" -- hydra -L users.txt -P pass.txt "$TARGET" http-post-form "/login:username=^USER^&password=^PASS^:F=Invalid" -o "$RUN/found.txt"`. Verify F=/S= markers before use.
4. Save secrets only as restricted evidence, never summary text. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'attack-ran=ok:run.log' --item 'results-recorded=ok:findings.md' --item 'lockout-safe=ok:notes/lockout.txt'`; add actual state fields and a secret-free verified finding or `no valid credentials found`.

## Modern tooling & alternatives
`hydra` is the general online brute across many protocols; `medusa` and `patator` are alternatives,
and `netexec` is preferred for SMB/WinRM/LDAP spraying at scale (lockout-aware). For **offline** hash
cracking use `hashcat`/`john`, not hydra.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and login-service endpoint checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: attack-ran
    desc: Brute/spray executed against the service and logged
    verify: nonempty
    evidence: run.log
    on_fail: redo-skill
    required: true
  - id: results-recorded
    desc: Run marker written (even when no creds found)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: lockout-safe
    desc: Threads throttled and lists targeted; no account lockouts caused
    verify: judge
    evidence: notes/lockout.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Account-lockout risk** — check the policy, throttle `-t`, and use small targeted lists; `lockout-safe` fails hard (`on_fail: fail`).
- HTTP forms: get the `F=`/`S=` marker right (a wrong failure string reports false positives); test the spec against a known-bad login first.
- `-f` stops after the first valid pair per host; drop it to enumerate all.
- For SMB/WinRM/LDAP at scale prefer `netexec` (lockout-aware); for offline hashes use `hashcat`.
- No valid credentials still finishes with that summary; the helper renders findings.md.
