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
1. Set up the run dir per AGENTS.md (`$RUN`); scope inherited from `out/<engagement>/scope.txt`. Fail fast on an empty file; `cp -a "$TARGET" "$RUN/" && cd "$RUN"` (extraction spawns many files — work in a scratch dir).
2. **Signature scan** (identify embedded content + offsets): `binwalk "$BN" 2>&1 | tee "$RUN/signatures.txt"`.
3. **Extract.** Carve what was found: `binwalk -e "$BN"` (add `--dd='<type>'` to force-carve a specific signature `-e` misses).
4. **Recurse if nested.** For firmware / matryoshka blobs: `binwalk -Me "$BN"`.
5. **Inspect + marker + hand-off.** Look through `_<file>.extracted/`; write a run marker (`no embedded content detected` if none), then `run.json`. Hand carved files to `ghidra`/`steghide`/`wireshark`.

## Modern tooling & alternatives
`binwalk` (v3 Rust rewrite) is the default; companions `foremost`/`scalpel` (header carving),
`file`/`strings` (triage), `bulk_extractor`. Chains with `exiftool` and stego tools.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); blob authorized for analysis
    verify: judge
    evidence: ../../scope.txt
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
- A run that finds nothing must still write `findings.md` ("no embedded content detected").
