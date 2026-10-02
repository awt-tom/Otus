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
---

# hydra — online login brute-forcing

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Confirm the target service is in scope **and check the account-lockout policy before brute-forcing** — online guessing can lock accounts and is noisy. Abort if the target is not confirmed in scope.

## Goal (desired outcome)
Find valid credentials on an online login service (ssh/ftp/rdp/smb/HTTP form) by testing a
user/password list — throttled to avoid lockouts — and record any valid logins for use by auth/web
skills.

## Steps
1. **Precondition / scope / lockout check.** Confirm the service is in scope and **read the lockout
   policy first**. Pick targeted user/password lists (small, context-driven — not blind rockyou
   against a lockout). Anchor a timestamped run directory to the repo root (never write under
   `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/hydra/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   TARGET="${1:?target host required}"; SERVICE="${2:?service (ssh/ftp/http-post-form/...) required}"
   echo "service $SERVICE on $TARGET confirmed in scope; lockout policy checked: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
2. **Run the attack** — `-L` userlist / `-P` passlist (or `-l`/`-p` for a single value), `-o` output,
   `-b json` for structured output, `-f` to stop on first valid pair, `-t` to throttle threads,
   `-s` for a non-default port. Usage is `hydra [options] <target> <service>`:
   ```bash
   hydra -L users.txt -P pass.txt -t 4 -f -o "$RUN/found.txt" -b json "$TARGET" "$SERVICE" 2>&1 | tee -a "$RUN/run.log"
   ```
3. **HTTP login forms** use the module's `"path:body:failure-string"` spec with `^USER^`/`^PASS^`
   placeholders (`F=` failure marker, or `S=` success marker):
   ```bash
   hydra -L users.txt -P pass.txt "$TARGET" http-post-form \
     "/login:username=^USER^&password=^PASS^:F=Invalid credentials" -o "$RUN/found.txt" 2>&1 | tee -a "$RUN/run.log"
   ```
4. **Record result + marker.** Always write a run marker so "ran but nothing" ≠ "didn't run":
   ```bash
   if grep -qiE '\[[0-9]+\]\[[a-z-]+\] host:|login:.*password:' "$RUN/found.txt" 2>/dev/null; then
     echo "hydra: valid login(s) found (see found.txt)" > "$RUN/summary.txt"
   else
     echo "no valid credentials found" > "$RUN/summary.txt"
   fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats). Feed valid creds to
   login / AD / web skills.

## Modern tooling & alternatives
`hydra` is the general online brute tool across many protocols; `medusa` and `patator` are
alternatives, and `netexec` is preferred for SMB/WinRM/LDAP spraying at scale (lockout-aware). For
**offline** hash cracking use `hashcat`/`john`, not hydra.

## Output formats
Text results (and `-b json` / `jsonv1` for structured) written via `-o` to `$RUN/found.txt`. This
skill also writes `$RUN/summary.txt` (run marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "hydra",
  "target": "<target> <service>",
  "run_dir": "out/hydra/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "attack-ran":       { "attempted": true, "ok": true, "evidence": "run.log" },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "lockout-safe":     { "attempted": true, "ok": true, "evidence": "notes/scope.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (hydra missing, service unreachable, bad
module spec, out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Shares the wordlist pool (rockyou/SecLists, CeWL for target-specific lists) — see §7. A per-service
module cheat-sheet (how to write the `http-post-form` spec, which services need extra params) is
useful RAG. Valid creds feed login/AD/web skills; prefer `netexec` for AD spraying.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target service confirmed in scope AND lockout policy checked before brute-forcing
    verify: judge
    evidence: notes/scope.txt
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
    evidence: summary.txt
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
- **Account-lockout risk** — check the policy, throttle `-t`, and use small targeted lists;
  `lockout-safe` fails hard (`on_fail: fail`).
- HTTP forms: get the `F=`/`S=` marker right (a wrong failure string reports false positives); test
  the spec against a known-bad login first.
- `-f` stops after the first valid pair per host; drop it to enumerate all.
- For SMB/WinRM/LDAP at scale prefer `netexec` (lockout-aware); for offline hashes use `hashcat`.
- A run that finds nothing must still write `summary.txt` ("no valid credentials found") so "ran but
  empty" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/hydra/<timestamp>/` (git-ignored).
