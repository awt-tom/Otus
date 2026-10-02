---
name: binwalk
description: >
  Use to detect and extract embedded or hidden files inside a blob (firmware image, picture, odd
  file) — the classic forensics/stego first move. Signature-scan, extract (-e), and recurse
  (-Me) into nested content, then hand carved output to RE/stego skills. Not for passphrase
  stego in images/audio (use steghide) or pcap analysis (use wireshark).
arguments: "file"
model: inherit
effort: low
context: inline
agent:
---

# binwalk — firmware/file carving & analysis

**Scope guard:** Authorized files only (CTF / lab / owned / in-scope). Only analyze and extract from files you are authorized to inspect. Abort if the file is not in scope.

## Goal (desired outcome)
Find and extract embedded/hidden files within a blob — revealing concatenated archives, filesystems,
or payloads — and pass the carved output to the next RE/stego step, with the signature report and
extraction captured.

## Steps
1. **Precondition / scope / scratch dir.** Confirm the file is in scope. Anchor a timestamped run
   directory to the repo root (never write under `skills/`) and work in it — extraction can spawn
   **many** files:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_binwalk="${OTUS_RUN_DIR:-$ROOT/out/binwalk/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_binwalk"
   mkdir -p "$RUN"
   TARGET="${1:?path to target file required}"
   [ -s "$TARGET" ] || { echo "file empty/missing: $TARGET" | tee -a "$RUN/run.log"; exit 1; }
   echo "file confirmed in scope: <who/when/program-or-lab>" > "$RUN/scope.txt"
   cp -a "$TARGET" "$RUN/"; cd "$RUN"; BN="$(basename "$TARGET")"
   ```
2. **Signature scan.** Identify embedded content and offsets:
   ```bash
   binwalk "$BN" 2>&1 | tee "$RUN/signatures.txt" | tee -a "$RUN/run.log"
   ```
3. **Extract.** Carve out what was found (`-e` auto-extract; `--dd=<type>` for a specific signature):
   ```bash
   binwalk -e "$BN" 2>&1 | tee -a "$RUN/run.log"
   ```
4. **Recurse if nested.** For firmware/matryoshka blobs, recurse into extracted content:
   ```bash
   binwalk -Me "$BN" 2>&1 | tee -a "$RUN/run.log"
   ```
5. **Inspect + marker + hand-off.** Look through the extraction dir (`_<file>.extracted/`), then
   always write a run marker so "scanned but empty" ≠ "didn't run":
   ```bash
   if ls -d "$RUN"/_*.extracted >/dev/null 2>&1 || [ -s "$RUN/signatures.txt" ]; then
     echo "binwalk: signatures/extraction present (see signatures.txt / _*.extracted)" > "$RUN/summary.txt"
   else echo "no embedded content detected" > "$RUN/summary.txt"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats). Hand carved files to
   RE (`ghidra`) / stego (`steghide`) / `wireshark`-carved follow-ups.

## Modern tooling & alternatives
`binwalk` (v3 Rust rewrite) is the default; companions `foremost` / `scalpel` (header-based carving),
`file` / `strings` (quick triage), `bulk_extractor` (bulk artifact carving). Chains with `exiftool`
and stego tools.

## Output formats
Extraction directory `_<file>.extracted/` (under `$RUN/`); signature report to stdout → saved as
`$RUN/signatures.txt`. This skill also writes `$RUN/summary.txt` (run marker), `$RUN/run.log`, and a
run record `$RUN/_run.json`:
```json
{
  "skill": "binwalk",
  "target": "<file>",
  "run_dir": "out/binwalk/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "scope.txt" },
    "scanned":          { "attempted": true, "ok": true, "evidence": "signatures.txt" },
    "extracted":        { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (binwalk missing, unreadable file, out of
scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Low RAG need. Chains with `exiftool` / stego (`steghide`, `zsteg`) and RE (`ghidra`); often the first
move on a mystery file before deciding which specialist skill to invoke next.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target file confirmed in scope before analysis/extraction
    verify: judge
    evidence: scope.txt
    on_fail: fail
    required: true
  - id: scanned
    desc: Signature scan run and report captured
    verify: nonempty
    evidence: signatures.txt
    on_fail: redo-skill
    required: true
  - id: extracted
    desc: Extraction attempted (-e / -Me); embedded content carved where present
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-part
    required: true
  - id: results-recorded
    desc: Run marker written (even when nothing embedded)
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Extraction can spawn many files** — always work in a scratch dir (the run directory), never in
  place.
- `-Me` recurses (matryoshka firmware); watch for extraction bombs on untrusted blobs.
- A clean `binwalk` scan doesn't mean "nothing hidden" — follow up with `steghide`/`zsteg`/`exiftool`
  and `strings` on the original.
- `--dd=<type>` carves a specific signature when `-e` misses it.
- A run that finds nothing must still write `summary.txt` ("no embedded content detected") so "ran
  but empty" ≠ "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/binwalk/<timestamp>/` (git-ignored).
