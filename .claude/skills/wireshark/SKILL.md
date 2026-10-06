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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/objects" "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Fail fast on an empty pcap; get a protocol overview first: `tshark -r "$PCAP" -q -z io,phs 2>&1 | tee "$RUN/notes/protocols.txt"`.
2. **Filter to interesting traffic.** Zoom in with display filters (`-Y http|ftp-data|dns|"tcp.stream eq N"`) and pull fields: `tshark -r "$PCAP" -Y "${2:-http}" -T fields -e frame.number -e ip.src -e http.request.full_uri` (or `-T json`).
3. **Follow streams.** Reconstruct a conversation in order with `-z follow,tcp,ascii,<stream>` to read creds/commands/exfil; save notable streams under `notes/`.
4. **Carve transferred files.** Export objects into the run dir (`--export-objects help` lists protocols): `tshark -r "$PCAP" --export-objects "http,$RUN/objects"` (also `smb`, `tftp`, `imf`, …).
5. **Record + marker + hand-off.** Write recovered creds/flags/artifacts + the filter used to `findings.md`; write a run marker (`no artifacts extracted` if none), then `run.json`. Feed carved files to `binwalk`/stego/crypto skills.

## Modern tooling & alternatives
Wireshark GUI for interactive exploration; `tshark` for scriptable/headless extraction (preferred
here); `tcpdump` to capture; `NetworkMiner` for automated carving. For huge pcaps, filter first (`-Y` / capture filter) before processing.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); capture authorized, recovered creds/PII handled responsibly
    verify: judge
    evidence: ../../scope.txt
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
- A run that extracts nothing must still write `findings.md` ("no artifacts extracted").
