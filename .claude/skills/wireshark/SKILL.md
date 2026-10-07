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
context: fork
agent: vuln-hunter
background: false
category: re-forensics
domain: forensics
---

# wireshark / tshark — packet analysis

Shared contract: see AGENTS.md.

## Goal
Extract the secrets/flags/artifacts hidden in a pcap — reconstruct conversations, carve transferred
files, decode protocols — capturing the recovered data and the filters used for the report.

## Steps
1. Offline capture: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill wireshark --profile selected-capture --coverage-set 'Sampled packet overview and at most three relevant streams/artifacts')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Verify nonempty PCAP/provenance and installed tshark/help. Write notes/task.md with hypothesis, actual packet/filter selection and <=120-second initial task; never modify the original capture.
2. Initial overview: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 60 --grace 5 -- tshark -n -r "$PCAP" -c 10000 -q -z io,phs > "$RUN/notes/protocols.txt"`. This samples at most 10000 packets; record sample/full-input difference. `-n` disables external name resolution; no live capture/network action.
3. Select a context-supported FILTER, not always HTTP. Use the checked helper with <=60-second cap and remaining allocation for `tshark -n -r "$PCAP" -Y "$FILTER" -T fields -e frame.number -e tcp.stream -e ip.src`, saving actual packet/stream refs. Select <=3 relevant streams/artifacts, not blanket follow/export.
4. Follow a selected stream with `-q -z "follow,tcp,ascii,$STREAM"` under the same bounded wrapper, writing private loot/ output. For selective object export first save the selected packets to evidence/selected.pcap with `-Y "$FILTER" -w`, then run the supported `--export-objects "http,$RUN/loot/objects"` on that selected capture, never presume an export-object job is restricted by display filtering alone. Record native object/files and exact filters in notes/assessment.md.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected packets, streams and object types' --item 'scope-confirmed=ok:../../scope.json' --item 'pcap-triaged=ok:notes/protocols.txt' --item 'artifacts-extracted=ok:notes/assessment.md' --item 'results-recorded=ok:notes/assessment.md' --target-state unchanged --cleanup not-needed`; finished declared sample can be complete with no artifacts, native unfinished/inconclusive partial, helper failure error. Add only artifact-backed secret-free findings; return candidate files to coordinator, no chained skill.

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
    desc: Actual selected-stream/object evidence supports claims, or justified skips disclosed
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
  - id: results-recorded
    desc: Sample/filter/stream coverage and actual artifacts or unknown counts accurately assessed
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Prefer `tshark`** for automation inside the skill; reserve the GUI for exploratory follow-stream work.
- Display filters restrict selected output, not necessarily decoding cost; sample/subset huge captures explicitly.
- Follow TCP/UDP streams to read creds/commands in order — a single-packet view misses the exchange.
- No artifacts still finishes with that summary; findings.md is generated.
