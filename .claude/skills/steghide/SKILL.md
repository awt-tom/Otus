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
1. Set up the run dir per AGENTS.md (`$RUN`); scope inherited from `out/<engagement>/scope.txt`. Fail fast on an empty file. Probe embedded data (unencrypted metadata reads without a passphrase): `steghide info "$SF" 2>&1 | tee "$RUN/info.txt"`.
2. **Extract with a passphrase** (empty passphrase is common in CTFs): `steghide extract -sf "$SF" -p "${2-}" -xf "$RUN/extracted.bin"` (`-sf` stego file, `-p` passphrase, `-xf` output).
3. **Crack the passphrase** when unknown: `stegseek "$SF" "${3:-/usr/share/wordlists/rockyou.txt}" "$RUN/extracted.bin"` (fast steghide cracker; writes the payload). Metadata-only probe: `stegseek --seed "$SF"`.
4. **Inspect the payload:** `file "$RUN/extracted.bin"; strings "$RUN/extracted.bin" | head`.
5. **Marker + hand-off + run record.** Write a run marker (`no payload extracted` if none), then `run.json`. Hand the payload to RE / crypto / `binwalk` follow-ups.

## Modern tooling & alternatives
`steghide` (JPEG/BMP/WAV/AU, passphrase) with `stegseek` for fast cracking; `zsteg` for PNG/BMP LSB;
`exiftool` for metadata; `binwalk`/`foremost` for carving; `*2john` + `john` for protected archives/docs. Pick the tool by container type — steghide ≠ zsteg.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); file authorized for analysis
    verify: judge
    evidence: ../../scope.txt
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
- A run that extracts nothing must still write `findings.md` ("no payload extracted").
