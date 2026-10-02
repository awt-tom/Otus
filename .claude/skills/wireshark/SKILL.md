---
name: wireshark
description: >
  Use to analyze a packet capture (pcap) and extract secrets/flags/artifacts — follow streams,
  carve transferred files, and decode protocols — preferring headless tshark for scriptable
  extraction inside the skill. Carved payloads feed binwalk/stego/crypto skills. Not for live
  attack traffic generation; this is analysis of an existing capture.
arguments: "pcap_file [display_filter]"
model: inherit
effort: medium
context: inline
agent:
---

# wireshark / tshark — packet analysis

**Scope guard:** Authorized captures only (CTF / lab / owned / in-scope). Only analyze pcaps you are authorized to inspect; handle any recovered credentials/PII responsibly. Abort if the capture is not in scope.

## Goal (desired outcome)
Extract the secrets/flags/artifacts hidden in a pcap — reconstruct conversations, carve transferred
files, and decode protocols — capturing the recovered data and the filters used for the report.

## Steps
1. **Precondition / scope / overview.** Confirm the capture is in scope. Anchor a timestamped run
   directory to the repo root (never write under `skills/`) and get a protocol overview first:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/wireshark/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/objects" "$RUN/notes"
   PCAP="${1:?path to pcap required}"
   [ -s "$PCAP" ] || { echo "pcap empty/missing: $PCAP" | tee -a "$RUN/run.log"; exit 1; }
   echo "capture confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   tshark -r "$PCAP" -q -z io,phs 2>&1 | tee "$RUN/notes/protocols.txt" | tee -a "$RUN/run.log"   # protocol hierarchy
   : > "$RUN/findings.md"
   ```
2. **Filter to interesting traffic.** Apply display filters (`-Y`) to zoom in — `http`, `ftp-data`,
   `dns`, `tcp.stream eq N` — and extract fields with `-T fields -e <field>` or `-T json`:
   ```bash
   tshark -r "$PCAP" -Y "${2:-http}" -T fields -e frame.number -e ip.src -e http.request.full_uri 2>&1 | tee -a "$RUN/run.log"
   ```
3. **Follow streams.** Reconstruct a conversation with `-z follow,tcp,ascii,<stream>` to read
   creds/commands/exfil in order; save notable streams under `notes/`.
4. **Carve transferred files.** Export objects for a protocol into the run dir (list protocols with
   `--export-objects help`):
   ```bash
   tshark -r "$PCAP" --export-objects "http,$RUN/objects" 2>&1 | tee -a "$RUN/run.log"   # also: smb, tftp, imf, ...
   ```
5. **Record findings + marker + hand-off.** Write recovered creds/flags/artifacts (and the filter
   used) to `findings.md`, then always write a run marker:
   ```bash
   if grep -qiE '^\- ' "$RUN/findings.md" || [ -n "$(ls -A "$RUN/objects" 2>/dev/null)" ]; then
     echo "wireshark: artifacts/streams extracted" > "$RUN/summary.txt"
   else echo "no artifacts extracted" > "$RUN/summary.txt"; echo "- none" >> "$RUN/findings.md"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats). Feed carved files to
   `binwalk` / stego / crypto skills.

## Modern tooling & alternatives
Wireshark GUI for interactive exploration; `tshark` for scriptable/headless extraction inside a skill
(preferred here); `tcpdump` to capture; `NetworkMiner` for automated artifact carving. For huge
pcaps, filter first (`-Y` / a capture filter) before processing.

## Output formats
Carved files via `--export-objects` (into `$RUN/objects/`); `tshark -T fields` / `-T json` for
structured extraction; CSV. This skill also writes `$RUN/notes/protocols.txt` (hierarchy),
`$RUN/findings.md` (recovered data + filters), `$RUN/summary.txt` (run marker), `$RUN/run.log`, and a
run record `$RUN/_run.json`:
```json
{
  "skill": "wireshark",
  "target": "<pcap_file>",
  "run_dir": "out/wireshark/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "pcap-triaged":     { "attempted": true, "ok": true, "evidence": "notes/protocols.txt" },
    "artifacts-extracted": { "attempted": true, "ok": true, "evidence": "findings.md" },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (tshark missing, unreadable pcap, out of
scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Useful RAG:** a filter/decode cheat-sheet (display filters per protocol, `--export-objects`
protocols, field names). Feeds `binwalk` / stego / crypto skills on carved payloads; recovered creds
feed login/AD skills.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Capture confirmed in scope before analysis; recovered creds/PII handled responsibly
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: pcap-triaged
    desc: Protocol hierarchy / overview captured to guide filtering
    verify: nonempty
    evidence: notes/protocols.txt
    on_fail: redo-part
    required: true
  - id: artifacts-extracted
    desc: Streams followed / objects carved; findings recorded (or documented "none")
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: results-recorded
    desc: Run marker written (even when nothing extracted)
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Prefer `tshark`** for automation inside the skill; reserve the GUI for exploratory follow-stream
  work.
- **Huge pcaps → filter first** (`-Y` / capture filter) or extraction crawls.
- `--export-objects help` lists supported protocols (http, smb, tftp, imf, …) — pick the right one.
- Follow TCP/UDP streams to read creds/commands in order; a single-packet view misses the exchange.
- A run that extracts nothing must still write `summary.txt` ("no artifacts extracted") and a
  `- none` line in `findings.md` so "ran but empty" ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/wireshark/<timestamp>/` (git-ignored).
