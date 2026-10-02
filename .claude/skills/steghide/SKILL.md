---
name: steghide
description: >
  Use to extract (or embed) data hidden in images/audio with steghide (passphrase-protected LSB
  stego) — pull a hidden payload with a known/guessed passphrase, probe with info, or crack the
  passphrase with stegseek + a wordlist. A forensics/stego companion; recovered payloads feed
  RE/crypto skills. Not for PNG/BMP LSB without steghide (use zsteg) or firmware carving (binwalk).
arguments: "stego_file [passphrase] [wordlist]"
model: inherit
effort: low
context: inline
agent:
---

# steghide — image/audio steganography extract & crack

**Scope guard:** Authorized files only (CTF / lab / owned / in-scope). Only extract from / embed into files you are authorized to handle. Abort if the file is not in scope.

## Goal (desired outcome)
Recover data hidden in an image/audio file with steghide — using a known/guessed passphrase, or by
cracking it with stegseek + a wordlist — and capture the extracted payload for the next step.

## Steps
1. **Precondition / scope / probe.** Confirm the file is in scope. Anchor a timestamped run directory
   to the repo root (never write under `skills/`) and probe for embedded data (unencrypted metadata
   is readable without a passphrase):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_steghide="${OTUS_RUN_DIR:-$ROOT/out/steghide/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_steghide"
   mkdir -p "$RUN"
   SF="${1:?path to stego file required}"
   [ -s "$SF" ] || { echo "stego file empty/missing: $SF" | tee -a "$RUN/run.log"; exit 1; }
   echo "file confirmed in scope: <who/when/program-or-lab>" > "$RUN/scope.txt"
   steghide info "$SF" 2>&1 | tee "$RUN/info.txt" | tee -a "$RUN/run.log" || true
   ```
2. **Extract with a passphrase** (empty passphrase is common in CTFs) — `-sf` stego file, `-p`
   passphrase, `-xf` output file:
   ```bash
   steghide extract -sf "$SF" -p "${2-}" -xf "$RUN/extracted.bin" 2>&1 | tee -a "$RUN/run.log"
   ```
3. **Crack the passphrase** when unknown — `stegseek <stegofile> <wordlist>` is a lightning-fast
   steghide cracker; it also writes the recovered payload:
   ```bash
   stegseek "$SF" "${3:-/usr/share/wordlists/rockyou.txt}" "$RUN/extracted.bin" 2>&1 | tee -a "$RUN/run.log"
   # metadata-only probe without a password: stegseek --seed "$SF"
   ```
4. **Inspect the payload.** Identify and read what came out:
   ```bash
   [ -s "$RUN/extracted.bin" ] && { file "$RUN/extracted.bin" | tee -a "$RUN/run.log"; strings "$RUN/extracted.bin" | head >> "$RUN/run.log"; }
   ```
5. **Marker + hand-off.** Always write a run marker so "tried but empty" ≠ "didn't run":
   ```bash
   if [ -s "$RUN/extracted.bin" ]; then echo "steghide: payload extracted (see extracted.bin)" > "$RUN/summary.txt";
   else echo "no payload extracted (no match / wrong passphrase)" > "$RUN/summary.txt"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats). Hand the payload to
   RE / crypto / `binwalk` follow-ups.

## Modern tooling & alternatives
`steghide` (JPEG/BMP/WAV/AU, passphrase) with `stegseek` for fast passphrase cracking; `zsteg` for
PNG/BMP LSB detection; `exiftool` for metadata; `binwalk`/`foremost` for carving. `*2john` + `john`
crack protected archives/docs. Pick the tool by container type — steghide ≠ zsteg.

## Output formats
Extracted payload file (`$RUN/extracted.bin`); `steghide info` report (`$RUN/info.txt`). This skill
also writes `$RUN/summary.txt` (run marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "steghide",
  "target": "<stego_file>",
  "run_dir": "out/steghide/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "scope.txt" },
    "probed":           { "attempted": true, "ok": true, "evidence": "info.txt" },
    "extract-attempted":{ "attempted": true, "ok": true, "evidence": "summary.txt" },
    "payload-recorded": { "attempted": true, "ok": true, "evidence": "extracted.bin" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (steghide missing, unreadable file, out of
scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Low RAG need. Shares the wordlist pool (rockyou/SecLists) with `hashcat`/`hydra` for passphrase
cracking. A stego-triage cheat-sheet ("which tool for which container") helps. Extracted payloads feed
`binwalk` / RE / crypto skills.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target file confirmed in scope before extract/embed
    verify: judge
    evidence: scope.txt
    on_fail: fail
    required: true
  - id: probed
    desc: File probed with steghide info (embedded-data check) and output captured
    verify: nonempty
    evidence: info.txt
    on_fail: redo-part
    required: true
  - id: extract-attempted
    desc: Extraction (and/or stegseek crack) attempted; run marker written
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: payload-recorded
    desc: Extracted payload saved (or documented "none")
    verify: exists
    evidence: extracted.bin
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- **Empty passphrase is common** in CTFs — try `-p ""` before cracking.
- steghide only handles JPEG/BMP/WAV/AU — for **PNG/BMP LSB** use `zsteg`, for metadata `exiftool`;
  picking the wrong tool wastes time.
- `stegseek` is thousands of times faster than legacy crackers and runs rockyou in seconds; use it
  when the passphrase is unknown. `stegseek --seed` detects steghide data without a password.
- Always `file`/`strings` the extracted payload — it may itself be another container to carve.
- A run that extracts nothing must still write `summary.txt` ("no payload extracted") so "ran but
  empty" ≠ "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/steghide/<timestamp>/` (git-ignored).
