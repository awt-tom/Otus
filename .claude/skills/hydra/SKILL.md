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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. **Read the account-lockout policy first**; pick small, targeted user/password lists.
2. **Run the attack** (`hydra [options] <target> <service>`): `hydra -L users.txt -P pass.txt -t 4 -f -o "$RUN/found.txt" -b json "$TARGET" "$SERVICE" 2>&1 | tee -a "$RUN/run.log"` (`-l`/`-p` single value, `-s` non-default port, `-f` stop on first hit, `-t` throttle threads).
3. **HTTP login forms** use the `"path:body:failure-string"` spec with `^USER^`/`^PASS^` placeholders (`F=` failure marker or `S=` success marker): `hydra -L users.txt -P pass.txt "$TARGET" http-post-form "/login:username=^USER^&password=^PASS^:F=Invalid" -o "$RUN/found.txt" 2>&1 | tee -a "$RUN/run.log"`.
4. **Record + marker.** If `found.txt` shows a valid login write the marker to `findings.md`, else `no valid credentials found`. Write `run.json`; feed valid creds to login / AD / web skills.

## Modern tooling & alternatives
`hydra` is the general online brute across many protocols; `medusa` and `patator` are alternatives,
and `netexec` is preferred for SMB/WinRM/LDAP spraying at scale (lockout-aware). For **offline** hash
cracking use `hashcat`/`john`, not hydra.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
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
    evidence: notes/scope.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Account-lockout risk** — check the policy, throttle `-t`, and use small targeted lists; `lockout-safe` fails hard (`on_fail: fail`).
- HTTP forms: get the `F=`/`S=` marker right (a wrong failure string reports false positives); test the spec against a known-bad login first.
- `-f` stops after the first valid pair per host; drop it to enumerate all.
- For SMB/WinRM/LDAP at scale prefer `netexec` (lockout-aware); for offline hashes use `hashcat`.
- A run that finds nothing must still write `findings.md` ("no valid credentials found").
