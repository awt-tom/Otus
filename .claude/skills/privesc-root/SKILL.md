---
name: privesc-root
description: >
  Use when escalating an authorized foothold to root and proving it — run the chosen
  privilege-escalation vector (SUID/sudo/cron/capability/kernel or a known-vulnerable
  local service), capture a non-destructive uid=0 transcript as proof, and grab
  /root/root.txt. Consumes a vector from linpeas/searchsploit or a foothold from
  metasploit/web-exploit. Not for enumeration (use linpeas) or framework exploitation
  (use metasploit).
arguments: "target [vector]"
model: inherit
effort: high
context: inline
agent:
---

# privesc-root — escalate to root, prove it, capture the flag

**Scope guard:** Authorized post-exploitation only (in-scope program / lab / owned) on a host you already have an authorized foothold on. Prefer the least-destructive proof of root. Abort if the host or foothold is not confirmed in scope.

## Goal (desired outcome)
Turn a confirmed vector into verified root on an authorized host: execute the escalation, capture a
non-destructive transcript that proves `uid=0(root)`, and record the root flag — producing certifiable
evidence (not a self-report) for review and reporting.

## Steps
1. **Precondition / scope / input.** Confirm the foothold/target is authorized and in scope. Anchor a
   timestamped run directory to the repo root (never write under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/privesc-root/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes" "$RUN/loot"
   TARGET="${1:?target/foothold host required}"
   echo "target $TARGET confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/version.txt"
   ```
2. **Identify & record the vector + version evidence.** Enumerate with the `linpeas` skill first, then
   pin down the exact vector and the version/reference that makes it exploitable (this is the proof the
   target was actually vulnerable). Use only what applies and record it:
   ```bash
   uname -a                           | tee -a "$RUN/notes/version.txt"   # kernel
   sudo -l 2>/dev/null                | tee -a "$RUN/notes/version.txt"   # sudo rules
   find / -perm -4000 -type f 2>/dev/null | tee -a "$RUN/notes/version.txt"  # SUID
   getcap -r / 2>/dev/null            | tee -a "$RUN/notes/version.txt"   # capabilities
   # for a vulnerable local service, capture its exact version banner, e.g.:
   #   <service> --version            | tee -a "$RUN/notes/version.txt"
   searchsploit <service/version>     | tee -a "$RUN/notes/version.txt"   # map version -> known exploit
   echo "chosen vector=<suid|sudo|cron|cap|kernel|service> ref=<CVE/GTFOBins>" >> "$RUN/notes/version.txt"
   ```
3. **Escalate (least-destructive).** Run the chosen vector to obtain a root context, teeing the **full**
   transcript — including any failed attempts, which corroborate the working path and the root cause:
   ```bash
   # <escalation command / hand-written PoC> 2>&1 | tee -a "$RUN/loot/root-shell.log"
   ```
4. **Prove root (non-destructive).** In the root context, run only read-only identity checks and capture
   them — this transcript is the certifiable proof:
   ```bash
   { id; whoami; hostname; } 2>&1 | tee "$RUN/loot/root-proof.txt"
   ```
5. **Capture the flag + marker.** Read the root flag if present; always write a marker so "proved root"
   is distinguishable from "no flag found":
   ```bash
   if cat /root/root.txt > "$RUN/notes/root-flag.txt" 2>/dev/null && [ -s "$RUN/notes/root-flag.txt" ]; then
     echo "root flag captured" | tee -a "$RUN/run.log"
   else
     echo "no /root/root.txt (root proven; flag absent or elsewhere)" > "$RUN/notes/root-flag.txt"
   fi
   ```
6. **Summarize + run record.** Write a run marker, then the run record `_run.json` into `$RUN/`
   (schema in Output formats):
   ```bash
   if grep -qi 'uid=0(root)' "$RUN/loot/root-proof.txt" 2>/dev/null; then
     echo "privesc-root: root proven on $TARGET (see loot/root-proof.txt)" > "$RUN/summary.txt"
   else
     echo "root not achieved — vector(s) tried, see loot/root-shell.log" > "$RUN/summary.txt"
   fi
   ```

## Modern tooling & alternatives
Enumerate first with `linpeas`/`pspy`; map findings to concrete abuse via **GTFOBins / LOLBAS** and
kernel/OS exploits via `linux-exploit-suggester` / `wesng`. Service CVEs come from `searchsploit` /
ExploitDB — a single hand-written PoC is often cleaner (and OSCP-friendlier) than a framework. Prefer
the least-destructive path; treat kernel exploits (which can crash the host) as a last resort.

## Output formats
Plaintext transcripts (`loot/root-shell.log`, `loot/root-proof.txt`) and notes (`notes/version.txt`,
`notes/root-flag.txt`), plus `summary.txt`, `run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "privesc-root",
  "target": "<target/foothold host>",
  "run_dir": "out/privesc-root/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":   { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "vector-identified": { "attempted": true, "ok": true, "evidence": "notes/version.txt" },
    "root-proven":       { "attempted": true, "ok": true, "evidence": "loot/root-proof.txt" },
    "flag-captured":     { "attempted": true, "ok": true, "evidence": "notes/root-flag.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (no foothold, vector not exploitable, out of
scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Consumes a vector from `linpeas` (enumeration), `searchsploit`/CVE notes (version → exploit), or a
foothold from `metasploit`/web-exploit. **Ideal RAG = GTFOBins + LOLBAS + HackTricks privesc**, turning
a finding (SUID binary, sudo rule, capability, vulnerable daemon) into a concrete escalation command.
Root access feeds reporting and, on domain-joined hosts, AD post-ex (`impacket`, `netexec`).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target/foothold confirmed in scope before any escalation step
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: vector-identified
    desc: Escalation vector and the exact vulnerable version/reference recorded
    verify: nonempty
    evidence: notes/version.txt
    on_fail: redo-part
    required: true
  - id: root-proven
    desc: Captured transcript proves root (uid=0) non-destructively
    verify: contains:uid=0\(root\)
    evidence: loot/root-proof.txt
    on_fail: redo-skill
    required: true
  - id: flag-captured
    desc: Root flag captured (or marker written if absent/elsewhere)
    verify: nonempty
    evidence: notes/root-flag.txt
    on_fail: redo-part
    required: true
```

## Notes / pitfalls
- **Scope first** — `scope-confirmed` fails hard (`on_fail: fail`); never escalate against an
  unconfirmed target.
- **Least-destructive proof** — prove root with `id`/`whoami`/`hostname` and read the flag; do not
  modify system files, add users, or dump more than needed.
- **Keep failed attempts** — retained failed transcripts corroborate the working vector and its root
  cause; don't delete them.
- **Record the version** — capture the exact vulnerable version/banner (`vector-identified`); "it
  worked" without the version isn't certifiable.
- **Kernel exploits can crash the host** — verify the version maps to the target and treat them as a
  last resort in labs; avoid in sensitive environments.
- A run that proves root but finds no `/root/root.txt` must still write the `notes/root-flag.txt`
  marker so "ran, proved root" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/privesc-root/<timestamp>/` (git-ignored).
