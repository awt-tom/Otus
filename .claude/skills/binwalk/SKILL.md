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
context: inline
agent:
category: re-forensics
domain: forensics
---

# binwalk — firmware / embedded-file extraction

Shared contract: see AGENTS.md.

## Goal
Find and extract embedded/hidden files within a blob — concatenated archives, filesystems, payloads —
and hand the carved output to the next RE/stego step, with the signature report + extraction captured.

## Steps
1. Offline artifact: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill binwalk)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Empty files finalize error. Copy the blob into RUN; export `RUN BN` for scratch-directory commands.
2. **Signature scan:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- bash -o pipefail -c 'cd "$RUN" && binwalk "$BN"' > "$RUN/signatures.txt"`.
3. **Extract:** wrap scratch-directory `binwalk -e "$BN"` with the same helper/shell form (add original `--dd='<type>'` if needed).
4. **Nested extraction:** wrap scratch-directory `binwalk -Me "$BN"` the same way; review extracted symlinks before any follow-up, never follow escapes.
5. Inspect carved files and hand off to ghidra/stego. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'scanned=ok:signatures.txt' --item 'extracted=ok:findings.md' --item 'results-recorded=ok:findings.md' --target-state unchanged --cleanup not-needed`; add secret-free artifact findings with real evidence, or `no embedded content detected`.

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
    verify: nonempty
    evidence: signatures.txt
    on_fail: redo-part
    required: true
  - id: extracted
    desc: Extraction attempted; carved files or documented "none"
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: results-recorded
    desc: Run marker written (even when nothing embedded)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Extraction spawns many files** — always work in a scratch dir (the run directory), never in place.
- `-Me` recurses (matryoshka firmware); watch for extraction bombs on untrusted blobs. `--dd='<type>'` carves a specific signature when `-e` misses it.
- A clean scan doesn't mean "nothing hidden" — follow up with `steghide`/`zsteg`/`exiftool` and `strings` on the original.
- No embedded content still finishes with that summary; the helper renders findings.md.
