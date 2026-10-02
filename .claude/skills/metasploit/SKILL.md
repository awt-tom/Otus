---
name: metasploit
description: >
  Use when exploiting a confirmed, authorized target with the Metasploit Framework
  (msfconsole) — select/configure an exploit or auxiliary module, run `check`, deliver a
  payload, and manage sessions / post-exploitation. Input is service/version detail from
  nmap. Not for content discovery (ffuf) or template scanning (nuclei); prefer single
  searchsploit/GitHub exploits for OSCP-style manual work.
arguments: "target_host [service_or_cve] [lhost]"
model: inherit
effort: high
context: inline
agent:
---

# metasploit — exploitation framework (msfconsole)

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Confirm the target host is in scope and set `LHOST` to your own listener on the lab/engagement network before running anything. Abort if the target is not confirmed in scope. **Autopwn / browser_autopwn are banned in the OSCP exam** and are noisy — do not use them.

## Goal (desired outcome)
Select, configure, and run the right exploit/auxiliary module against an authorized target —
validating with `check` before firing, delivering a payload, and managing the resulting
session / post-exploitation — with the full console transcript captured for the report.

## Steps
1. **Precondition / scope / inputs.** Confirm the host is in scope and gather `nmap` service/
   version output to drive module selection. Determine the correct `LHOST` for the lab network.
   Anchor a timestamped run directory to the repo root (never write under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_metasploit="${OTUS_RUN_DIR:-$ROOT/out/metasploit/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_metasploit"
   mkdir -p "$RUN/notes"
   RHOST="${1:?target_host required}"; LHOST="${3:-<your-lhost>}"
   echo "target $RHOST confirmed in scope; LHOST=$LHOST: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/modules.txt"
   ```
2. **Launch + spool the session.** Start the console quietly and spool the whole transcript into
   the run directory so the run is evidenced:
   ```bash
   msfconsole -q
   # inside msfconsole:
   #   spool <RUN>/run.log
   #   workspace -a <engagement>
   ```
3. **Search → select → configure.** `search <service/cve>` to find candidate modules (record the
   chosen module + options in `notes/modules.txt`), then `use <module>` and
   `set RHOSTS <target>` / `set LHOST <you>` / `set payload <payload>`.
4. **`check` before `run`.** Where the module supports it, run `check` first and only `run` /
   `exploit` on a positive (or deliberately-justified) result — avoid noisy auto-exploitation.
   **Never** use Autopwn / browser_autopwn. Record what was fired in `notes/modules.txt`.
5. **Session / post-ex + marker.** On a session: `sessions -i <id>`, run post modules, `migrate`,
   and loot; `db_export -f xml <RUN>/workspace.xml` to save the workspace. Always write a run
   marker so "ran but no session" ≠ "didn't run":
   ```bash
   if grep -qiE "session [0-9]+ opened|Meterpreter session|Command shell session" "$RUN/run.log"; then
     echo "metasploit: session opened (see run.log + workspace.xml)" > "$RUN/summary.txt"
   else
     echo "no session — module(s) tried, no shell" > "$RUN/summary.txt"
     echo "none opened" >> "$RUN/notes/modules.txt"
   fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
`msfconsole` is still the standard framework. For manual / OSCP-style work prefer single exploits
from `searchsploit` / ExploitDB / GitHub (run them by hand). `msfvenom` generates standalone
payloads/shellcode when you don't want the full framework.

## Output formats
Console output; `spool <file>` mirrors the session to `$RUN/run.log`; loot/notes live in the
workspace DB and are exported via `db_export -f xml` to `$RUN/workspace.xml`. This skill also writes
`$RUN/notes/modules.txt` (modules + options tried), `$RUN/summary.txt` (run marker), and a run
record `$RUN/_run.json`:
```json
{
  "skill": "metasploit",
  "target": "<target_host>",
  "run_dir": "out/metasploit/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed": { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "module-selected": { "attempted": true, "ok": true, "evidence": "notes/modules.txt" },
    "run-executed":    { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "check-before-run":{ "attempted": true, "ok": true, "evidence": "run.log" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (msfconsole missing, target unreachable,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Module selection is driven by `searchsploit` / ExploitDB + CVE notes (RAG) matched against `nmap`
service/version output. Confirmed sessions feed post-exploitation (privesc / `impacket` /
`netexec`) and reporting. `msfvenom` payloads pair with manual delivery.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target host confirmed in scope and LHOST set for the lab network before running
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: module-selected
    desc: Module searched, selected, and configured (RHOSTS/LHOST/payload) — recorded
    verify: nonempty
    evidence: notes/modules.txt
    on_fail: redo-part
    required: true
  - id: run-executed
    desc: Module executed; run marker written (even if no session opened)
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: check-before-run
    desc: '`check` used before `run` where supported; no Autopwn/browser_autopwn (OSCP-banned)'
    verify: judge
    evidence: run.log
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Use `check` before `run`** and avoid noisy auto-exploitation; `check-before-run` fails hard
  (`on_fail: fail`).
- **Autopwn / browser_autopwn are banned in the OSCP exam** and indiscriminate — do not use them.
- Set `LHOST` to the correct interface for the lab/engagement network, or your payload never calls
  back.
- For OSCP-style manual work, prefer single `searchsploit`/GitHub exploits over the framework.
- A run that opens no session must still write `summary.txt` ("no session …") and
  `notes/modules.txt` so "ran but empty" ≠ "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/metasploit/<timestamp>/` (git-ignored).
