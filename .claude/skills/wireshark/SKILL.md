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
category: re-forensics
domain: forensics
---

# wireshark / tshark — packet analysis

Shared contract: see AGENTS.md.

## Goal
Extract the secrets/flags/artifacts hidden in a pcap — reconstruct conversations, carve transferred
files, decode protocols — capturing the recovered data and the filters used for the report.

## Steps
1. Offline capture: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill wireshark)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Empty captures finalize error. `mkdir -p "$RUN/objects"`; `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- tshark -r "$PCAP" -q -z io,phs > "$RUN/notes/protocols.txt"`.
2. **Filter:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- tshark -r "$PCAP" -Y "${2:-http}" -T fields -e frame.number -e ip.src -e http.request.full_uri` (or original `-T json`).
3. **Follow streams.** Reconstruct a conversation in order with `-z follow,tcp,ascii,<stream>` to read creds/commands/exfil; save notable streams under `notes/`.
4. **Carve transferred files.** Export objects into the run dir (`--export-objects help` lists protocols): `tshark -r "$PCAP" --export-objects "http,$RUN/objects"` (also `smb`, `tftp`, `imf`, …).
5. Follow/export commands use the same helper wrapper; secrets go to `loot/`, filters/decisions to `notes/`, and findings refer to evidence without secret values. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'pcap-triaged=ok:notes/protocols.txt' --item 'artifacts-extracted=ok:findings.md' --item 'results-recorded=ok:findings.md' --target-state unchanged --cleanup not-needed`; add verified artifact findings or `no artifacts extracted`. Hand off to binwalk/stego/crypto.

## Modern tooling & alternatives
Wireshark GUI for interactive exploration; `tshark` for scriptable/headless extraction (preferred
here); `tcpdump` to capture; `NetworkMiner` for automated carving. For huge pcaps, filter first (`-Y` / capture filter) before processing.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and capture provenance checked; PII handled responsibly
    verify: judge
    evidence: ../../scope.json
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
    evidence: findings.md
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Prefer `tshark`** for automation inside the skill; reserve the GUI for exploratory follow-stream work.
- **Huge pcaps → filter first** (`-Y` / capture filter) or extraction crawls; `--export-objects help` lists supported protocols (http, smb, tftp, imf, …).
- Follow TCP/UDP streams to read creds/commands in order — a single-packet view misses the exchange.
- No artifacts still finishes with that summary; findings.md is generated.
