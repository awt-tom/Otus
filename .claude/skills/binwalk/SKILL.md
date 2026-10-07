---
name: binwalk
description: >
  Use to detect and extract embedded or hidden files inside a blob (firmware image, picture, odd
  file) — the classic forensics/stego first move. Signature-scan, extract (-e), and recurse (-Me)
  into nested content, then hand carved output to RE/stego skills. Not for passphrase stego in
  images/audio (use steghide) or pcap analysis (use wireshark).
arguments: "target_file [--dd type]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: re-forensics
domain: forensics
---

# binwalk — firmware / embedded-file extraction

Shared contract: see AGENTS.md.

## Goal
Find and extract embedded/hidden files within a blob — concatenated archives, filesystems, payloads —
and hand the carved output to the next RE/stego step, with the signature report + extraction captured.

## Steps
1. Offline artifact: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill binwalk --profile signature-first --coverage-set 'One blob signature scan; selective extraction only with a lead')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Verify nonempty input/provenance and installed version/help. Copy the blob to private scratch without modifying original; BN is an absolute scratch path. Write notes/task.md with hypothesis, <=60-second command caps and <=180-second total allocation.
2. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 60 --grace 5 -- binwalk "$BN" > "$RUN/signatures.txt"`. Inspect actual offsets/container signatures; a signature is a lead, not verified carved content. No default extraction/recursive sweep.
3. A matched container/objective may justify one selective extraction in private scratch, using only installed-version-supported options/decompressors and the same 60-second helper cap. Preflight enforceable extraction limits: <=100 files, <=100 MiB total and <=2 layers. Monitor actual count/bytes/depth, not just a post-hoc estimate; if enforcement is unavailable, skip recursion/extraction and disclose the limitation. No invented limit flags or unlimited `-Me`.
4. Preserve native outputs; verify actual carved file types/content and offsets, never execute them or follow symlink/path escapes. A further layer needs a specific signature lead and remaining limits/allocation; stop at the declared limits with truthful partial coverage. Record actual files/count/bytes or unknown values, skips and extraction decision in notes/assessment.md. Empty signature results do not exclude other stego formats.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected containers and deeper extraction' --item 'scope-confirmed=ok:../../scope.json' --item 'scanned=ok:signatures.txt' --item 'extracted=ok:notes/assessment.md' --item 'results-recorded=ok:notes/assessment.md' --target-state unchanged --cleanup not-needed`; selected signature-only task can be complete, native budget/unenforceable needed extraction partial, helper failure error. Add only artifact-backed findings; return candidate files to coordinator, no chained skill.

## Modern tooling & alternatives
`binwalk` (v3 Rust rewrite) is the default; companions `foremost`/`scalpel` (header carving),
`file`/`strings` (triage), `bulk_extractor`. Chains with `exiftool` and stego tools.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and blob provenance checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: scanned
    desc: Signature scan captured (embedded content + offsets)
    verify: judge
    evidence: signatures.txt
    on_fail: redo-part
    required: true
  - id: extracted
    desc: Actual carved files substantiate claims, or justified skip/limits accurately disclosed
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
  - id: results-recorded
    desc: Offsets, actual extraction limits/coverage and omissions match native artifacts
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Extraction spawns many files** — always work in a scratch dir (the run directory), never in place.
- Recursive decompression can exceed disk/memory before a time cap; elapsed time alone is not a size/file sandbox.
- Format-specific stego/carving is a proposed next hypothesis, not automatic follow-up to an empty scan.
- No embedded content still finishes with that summary; the helper renders findings.md.
