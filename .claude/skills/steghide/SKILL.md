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
context: fork
agent: vuln-hunter
background: false
category: re-forensics
domain: forensics
---

# steghide — image/audio steganography extraction

Shared contract: see AGENTS.md.

## Goal
Recover data hidden in an image/audio file with steghide — using a known/guessed passphrase or by
cracking it with stegseek + a wordlist — and capture the extracted payload for the next step.

## Steps
1. Offline artifact: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill steghide --profile selected-stego --coverage-set 'One supported container and selected passphrase/extraction hypothesis')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Verify nonempty SF/provenance and installed help/version. Write notes/task.md with actual container, supplied-passphrase or justified finite cracking choice, <=60-second command cap and <=90-second total allocation.
2. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- file "$SF" > "$RUN/info.txt"`; steghide supports JPEG/BMP/WAV/AU, not PNG. Unsupported format -> partial/not-applicable, no blind steghide/cracker sequence. Optional embedded-info uses explicit `steghide info "$SF" -p "$PASS"` under a 10-second helper only when needed; never the prompting bare-info form.
3. Supplied passphrase branch: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 60 --grace 5 -- steghide extract -sf "$SF" -p "$PASS" -xf "$RUN/loot/extracted.bin"`. Empty PASS is an explicitly selected hypothesis, not a mandatory attempt. Unknown passphrase with a credible container lead may instead justify one bounded contextual dictionary: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 60 --grace 5 -- stegseek "$SF" "$WL" "$RUN/loot/extracted.bin"`; no default rockyou/seed/guess ladder. Any prompt/nonzero is error; stop, do not fall through to another branch.
4. Only after normal success, inspect the actual payload with a <=10-second helper `file`/bounded strings view, preserving raw payload under loot/. Record real artifact refs, tested/omitted hypotheses and no-confirmation/format limitations in notes/assessment.md; never execute extracted content. A failure/prompt is not no hidden data.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected passphrases and stego formats' --item 'scope-confirmed=ok:../../scope.json' --item 'probed=ok:info.txt' --item 'extract-attempted=ok:notes/assessment.md' --target-state unchanged --cleanup not-needed`; complete only finished declared extraction, unknown/unsupported partial, helper nonzero error. Add artifact-backed secret-free findings and return candidate payload to coordinator, no chained runbook.

## Modern tooling & alternatives
`steghide` (JPEG/BMP/WAV/AU, passphrase) with `stegseek` for fast cracking; `zsteg` for PNG/BMP LSB;
`exiftool` for metadata; `binwalk`/`foremost` for carving; `*2john` + `john` for protected archives/docs. Pick the tool by container type — steghide ≠ zsteg.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and stego-file provenance checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: probed
    desc: Actual supported-format/optional noninteractive metadata evidence captured
    verify: judge
    evidence: info.txt
    on_fail: redo-part
    required: true
  - id: extract-attempted
    desc: Events/native output prove selected extraction or justified no-launch, coverage honest
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
  - id: payload-recorded
    desc: Extracted payload captured when one was recovered
    verify: judge
    evidence: loot/extracted.bin
    on_fail: fail
    required: false
```

## Notes / pitfalls
- Empty passphrase is one contextual hypothesis, not a mandatory prerequisite to a supplied passphrase.
- steghide only handles JPEG/BMP/WAV/AU — for **PNG/BMP LSB** use `zsteg`, metadata `exiftool`; wrong tool wastes time.
- Runtime depends on input/backend/dictionary; never promise a seconds-to-solve guarantee.
- No payload still finishes with that summary; findings.md is generated.
