---
name: steghide
description: >
  Use to extract (or embed) data hidden in images/audio with steghide (passphrase-protected LSB
  stego) — pull a hidden payload with a known/guessed passphrase, probe with info, or crack the
  passphrase with stegseek + a wordlist. A forensics/stego companion; recovered payloads feed
  RE/crypto skills. Not for PNG/BMP LSB without steghide (use zsteg) or firmware carving (binwalk).
arguments: "stego_file [passphrase] [wordlist]"
model: inherit
effort: medium
context: inline
agent:
category: re-forensics
domain: forensics
---

# steghide — image/audio steganography extraction

Shared contract: see AGENTS.md.

## Goal
Recover data hidden in an image/audio file with steghide — using a known/guessed passphrase or by
cracking it with stegseek + a wordlist — and capture the extracted payload for the next step.

## Steps
1. Offline artifact: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill steghide)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Empty files finalize error. `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- steghide info "$SF" > "$RUN/info.txt"`; a prompting form is a tool failure, not an interactive retry.
2. **Extract:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- steghide extract -sf "$SF" -p "${2-}" -xf "$RUN/extracted.bin"` (empty passphrase common).
3. **Crack when unknown:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- stegseek "$SF" "${3:-/usr/share/wordlists/rockyou.txt}" "$RUN/extracted.bin"`; metadata-only `stegseek --seed "$SF"` uses the same wrapper.
4. Helper-wrap `file "$RUN/extracted.bin"` and `strings "$RUN/extracted.bin"`; keep secret contents out of summary/event notes.
5. Hand payload to RE/crypto/binwalk. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'probed=ok:info.txt' --item 'extract-attempted=ok:findings.md' --target-state unchanged --cleanup not-needed`; add artifact-backed, secret-free `--finding` entries or `no payload extracted`.

## Modern tooling & alternatives
`steghide` (JPEG/BMP/WAV/AU, passphrase) with `stegseek` for fast cracking; `zsteg` for PNG/BMP LSB;
`exiftool` for metadata; `binwalk`/`foremost` for carving; `*2john` + `john` for protected archives/docs. Pick the tool by container type — steghide ≠ zsteg.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and stego-file provenance checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: probed
    desc: steghide info probe captured (format / embedded-data check)
    verify: nonempty
    evidence: info.txt
    on_fail: redo-part
    required: true
  - id: extract-attempted
    desc: Extraction / crack attempted; result recorded (or documented "none")
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: payload-recorded
    desc: Extracted payload captured when one was recovered
    verify: exists
    evidence: extracted.bin
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- **Empty passphrase is common** in CTFs — try `-p ""` before cracking.
- steghide only handles JPEG/BMP/WAV/AU — for **PNG/BMP LSB** use `zsteg`, metadata `exiftool`; wrong tool wastes time.
- `stegseek` runs rockyou in seconds (`--seed` detects steghide data without a password); always `file`/`strings` the payload — it may be another container to carve.
- No payload still finishes with that summary; findings.md is generated.
