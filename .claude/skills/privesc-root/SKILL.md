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
> **Foothold transport (read first).** The operator's Claude Code Bash tool runs each command in a
> **fresh, one-shot LOCAL shell** on the operator box — it does **not** hold a live interactive shell
> on the target between calls. Every **target-side** command below must therefore run **through an
> explicit transport** to your foothold, chosen and recorded in `notes/transport.txt`:
> - **SSH** (preferred when credentialed; stateless): `ssh user@target '<cmd>'` with a key/creds.
> - **Webshell / RCE one-shot:** send each command as a fresh request through the exploit channel that
>   returns its output.
> - **Persistent reverse shell in tmux/screen:** `tmux send-keys` to run, `tmux capture-pane` to read.
>
> Never assume a held interactive session survives between steps. Always **tee the target-side output
> back into the local run dir** (`notes/enum.txt`, `loot/root-shell.log`, `loot/root-proof.txt`) as
> evidence. The command blocks below show the **target-side** commands — wrap each in your chosen
> transport; operator-side lookups (e.g. `searchsploit`) run locally and are marked as such.

1. **Precondition / scope / input.** Confirm the foothold/target is authorized and in scope. Anchor a
   timestamped run directory to the repo root (never write under `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_privesc_root="${OTUS_RUN_DIR:-$ROOT/out/${ENGAGEMENT:?engagement slug required}/privesc-root/$(date -u +%Y%m%dT%H%M%SZ)}"
   RUN="$OTUS_RUN_privesc_root"
   started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
   mkdir -p "$RUN/notes" "$RUN/loot"
   TARGET="${1:?target/foothold host required}"
   echo "target $TARGET confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   echo "transport=<ssh user@host | webshell:<url> | revshell:tmux:<session>> reason=<why chosen>" > "$RUN/notes/transport.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/enum.txt"; : > "$RUN/notes/version.txt"
   ```
2. **Enumerate, then identify & record the vector.** Run the `linpeas` skill (plus the checks below) to
   capture enumeration into `notes/enum.txt`, then pin down the exact vector and the version/reference
   that makes it exploitable (the proof the target was vulnerable) into `notes/version.txt`:
   ```bash
   # --- run IN THE FOOTHOLD via your chosen transport; tee output into the local run dir ---
   TGT='ssh user@target'   # or: send the braced block through your webshell/RCE channel / tmux
   $TGT '{ uname -a; sudo -l 2>/dev/null; find / -perm -4000 -type f 2>/dev/null; getcap -r / 2>/dev/null; }' \
     2>&1 | tee -a "$RUN/notes/enum.txt"                 # kernel / sudo rules / SUID / capabilities
   # vulnerable local service — capture its exact version banner FROM THE FOOTHOLD, e.g.:
   #   $TGT '<service> --version' 2>&1 | tee -a "$RUN/notes/enum.txt"
   # --- run LOCALLY on the operator box (ExploitDB lookup, no target contact): ---
   searchsploit <service/version> | tee -a "$RUN/notes/enum.txt"   # map version -> known exploit
   # record the CHOSEN vector + the exact version/reference that proves exploitability:
   echo "vector=<suid|sudo|cron|cap|kernel|service> version=<exact version> ref=<CVE/GTFOBins>" \
     | tee -a "$RUN/notes/version.txt"
   ```
3. **Escalate (least-destructive).** Run the chosen vector to obtain a root context, teeing the **full**
   transcript — including any failed attempts, which corroborate the working path and the root cause:
   ```bash
   # run the escalation IN THE FOOTHOLD via your transport; tee the full transcript locally:
   #   ssh user@target '<escalation command / hand-written PoC>' 2>&1 | tee -a "$RUN/loot/root-shell.log"
   #   (webshell/RCE: send the command through the channel; revshell: tmux send-keys + capture-pane)
   ```
4. **Prove root (non-destructive).** In the root context, run only read-only identity checks and capture
   them — this transcript is the certifiable proof:
   ```bash
   # execute the identity checks IN THE ROOT CONTEXT ON THE TARGET; tee the proof locally:
   ssh user@target 'id; whoami; hostname' 2>&1 | tee "$RUN/loot/root-proof.txt"
   #   (or send `id; whoami; hostname` through the webshell/RCE channel, or tmux capture-pane)
   ```
5. **Capture the flag + marker.** Read the root flag if present; always write a marker so "proved root"
   is distinguishable from "no flag found":
   ```bash
   # read the flag FROM THE TARGET via your transport (ssh shown; or webshell/RCE channel):
   if ssh user@target 'cat /root/root.txt' > "$RUN/notes/root-flag.txt" 2>/dev/null && [ -s "$RUN/notes/root-flag.txt" ]; then
     echo "root flag captured" | tee -a "$RUN/run.log"
   else
     echo "no /root/root.txt (root proven; flag absent or elsewhere)" > "$RUN/notes/root-flag.txt"
   fi
   ```
6. **Summarize + run record.** Write a run marker, then the run record `run.json` into `$RUN/`
   (schema in Output formats):
   ```bash
   if grep -qi 'uid=0(root)' "$RUN/loot/root-proof.txt" 2>/dev/null; then
    echo "privesc-root: root proven on $TARGET (see loot/root-proof.txt)" > "$RUN/findings.md"
   else
    echo "root not achieved — vector(s) tried, see loot/root-shell.log" > "$RUN/findings.md"
   fi
   ```

## Modern tooling & alternatives
Enumerate first with `linpeas`/`pspy`; map findings to concrete abuse via **GTFOBins / LOLBAS** and
kernel/OS exploits via `linux-exploit-suggester` / `wesng`. Service CVEs come from `searchsploit` /
ExploitDB — a single hand-written PoC is often cleaner (and OSCP-friendlier) than a framework. Prefer
the least-destructive path; treat kernel exploits (which can crash the host) as a last resort.

## Output formats
Plaintext transcripts (`loot/root-shell.log`, `loot/root-proof.txt`) and notes (`notes/enum.txt`,
`notes/version.txt`, `notes/root-flag.txt`), plus `findings.md`, `run.log`, and a run record `$RUN/run.json`:
```json
{
  "skill": "privesc-root",
  "engagement": "<engagement slug>",
  "target": "<target/foothold host>",
  "run_dir": "out/<engagement>/privesc-root/<timestamp>",
  "started": "<started: date -u +%Y-%m-%dT%H:%M:%SZ, ISO-8601 UTC>",
  "finished": "<finished: date -u at finish; must be >= started>",
  "status": "complete",
  "summary": "<one line>",
  "evidence": ["findings.md"],
  "items": {
    "scope-confirmed":   { "ok": true, "evidence": "notes/scope.txt" },
    "run-log":           { "ok": true, "evidence": "run.log" },
    "transport-recorded":{ "ok": true, "evidence": "notes/transport.txt" },
    "enum-ran":          { "ok": true, "evidence": "notes/enum.txt" },
    "vector-identified": { "ok": true, "evidence": "notes/version.txt" },
    "root-proof":        { "ok": true, "evidence": "loot/root-proof.txt" },
    "run-record":        { "ok": true, "evidence": "run.json" }
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
  - id: run-log
    desc: Run log initialized and written to the run directory
    verify: exists
    evidence: run.log
    on_fail: redo-part
    required: true
  - id: transport-recorded
    desc: Foothold transport (ssh / webshell-RCE / reverse-shell) recorded so the channel to the target is auditable
    verify: nonempty
    evidence: notes/transport.txt
    on_fail: redo-part
    required: true
  - id: enum-ran
    desc: Privilege-escalation enumeration executed and captured
    verify: nonempty
    evidence: notes/enum.txt
    on_fail: redo-part
    required: true
  - id: vector-identified
    desc: Chosen escalation vector + exact vulnerable version/reference recorded
    verify: judge
    evidence: notes/version.txt
    on_fail: redo-part
    required: true
  - id: root-proof
    desc: Captured transcript proves root (uid=0) non-destructively
    verify: contains:uid=0
    evidence: loot/root-proof.txt
    on_fail: redo-skill
    required: true
  - id: run-record
    desc: Run record run.json written for the run
    verify: exists
    evidence: run.json
    on_fail: redo-part
    required: true
```

## Notes / pitfalls
- **Scope first** — `scope-confirmed` fails hard (`on_fail: fail`); never escalate against an
  unconfirmed target.
- **Local shell is one-shot** — the operator Bash tool holds no session on the target; run every
  target-side command through the recorded transport (`notes/transport.txt`) and tee its output back
  into the local run dir. A command run locally by mistake proves nothing about the target.
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
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `run.json` (`status: error`, block type + request id in `errors[]`) and `findings.md` recording the stop,
  then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- **Cleanup verification:** if you planted any artifact on the target (file, user, cron, implant),
  verify its removal with positive evidence to `loot/cleanup_verify.txt` before declaring clean; on an
  aborted run, record the owed cleanup in `findings.md`.
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/<engagement>/privesc-root/<timestamp>/` (git-ignored).
