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
context: fork
agent: vuln-hunter
background: false
category: access
domain: network
---

# hydra — online login brute-forcing

Shared contract: see AGENTS.md.

## Goal
Find valid credentials on an online login service (ssh/ftp/rdp/smb/HTTP form) by testing a
user/password list — throttled to avoid lockouts — and record any valid logins for auth/web skills.

## Steps
1. This is a conditional credential hypothesis, never a default attack. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill hydra --target "$TARGET" --profile targeted-pairs --coverage-set 'At most ten selected credential pairs within known lockout allowance')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with verified version/service, known lockout policy, per-account/aggregate prior attempts and a <=60-second initial allocation.
2. Unknown policy/remaining allowance -> not-tested/partial, no spray. Save policy, exact approved attempt budget and observed/unknown effects in notes/lockout.txt. Select <=10 context-supported user:password pairs to private PAIRS; baseline/validation attempts count against the same allowance. No userlist/passwordlist Cartesian product or automatic wordlist expansion.
3. Run with private cwd so restore state remains in RUN: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 60 --grace 5 -- bash -o pipefail -c 'cd "$1" && shift && exec "$@"' otus-hydra "$RUN" hydra -C "$PAIRS" -I -t 1 -f -o "$RUN/evidence/hydra.json" -b json "$TARGET" "$SERVICE"`. PAIRS is absolute. `-I` prevents restore prompts; preserve native files and inspect installed help before use.
4. HTTP form is an alternative selected SERVICE/spec, not another ladder step; verify failure/success controls first within allowance. Validate at most the first hit using the owning protocol's bounded one-shot form, only if allowance remains and the command ended normally; no automatic reconnect after failure. Stop on lockout/degradation, no wait/retry.
5. Record actual tested/skipped pairs, native outcome and proof refs in notes/results.md. Native no-hit can be a scoped negative; arbitrary nonzero remains error. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected credentials and services' --item 'scope-confirmed=ok:../../scope.json' --item 'attack-ran=ok:events.jsonl' --item 'results-recorded=ok:notes/results.md' --item 'lockout-safe=ok:notes/lockout.txt'`; include actual state/cleanup and only a secret-free verified finding. Never claim no lockout without evidence; return to coordinator.

## Modern tooling & alternatives
`hydra` is the general online brute across many protocols; `medusa` and `patator` are alternatives,
and `netexec` is preferred for SMB/WinRM/LDAP spraying at scale (lockout-aware). For **offline** hash
cracking use `hashcat`/`john`, not hydra.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and login-service endpoint checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: attack-ran
    desc: Events and native output prove selected attempts or explicitly withheld attack
    verify: judge
    evidence: events.jsonl
    on_fail: fail
    required: true
  - id: results-recorded
    desc: Actual counts/outcome and any claimed hit match native proof, omissions disclosed
    verify: judge
    evidence: notes/results.md
    on_fail: fail
    required: true
  - id: lockout-safe
    desc: Policy and aggregate/per-account allowance respected; actual or unknown effects honest
    verify: judge
    evidence: notes/lockout.txt
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Account-lockout risk** — check the policy, throttle `-t`, and use small targeted lists; `lockout-safe` fails hard (`on_fail: fail`).
- HTTP forms: get the `F=`/`S=` marker right (a wrong failure string reports false positives); test the spec against a known-bad login first.
- `-f` stops after the first valid pair per host; no default all-credential collection.
- For SMB/WinRM/LDAP at scale prefer `netexec` (lockout-aware); for offline hashes use `hashcat`.
- No valid credentials still finishes with that summary; the helper renders findings.md.
