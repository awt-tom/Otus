---
name: ffuf
description: >
  Use when fuzzing a web target for hidden directories, files, parameters, or virtual
  hosts — content discovery / directory brute-forcing with ffuf. Wordlist-driven; its
  hits feed LFI/upload/IDOR and manual/Burp testing. Not for subdomain discovery
  (use subfinder) or template-based vuln scanning (use nuclei).
arguments: "target_url wordlist [output]"
model: inherit
effort: low
context: fork
agent: general-purpose
category: recon
domain: web
---

# ffuf — web fuzzer (dirs, files, params, vhosts)

Shared contract: see AGENTS.md.

## Goal
Discover hidden paths, files, parameters, and virtual hosts on an in-scope web target, producing a
calibrated, low-false-positive list of hits to drive manual and vuln-class testing.

## Steps
1. Put `FUZZ` in the path/parameter of `target`; choose `WORDLIST`. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ffuf --target "$target")"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$target" --run-dir "$RUN"`; nonzero STOP.
2. **Calibrate:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" -- ffuf -u "${target/FUZZ/ffuf-calibrate-$RANDOM}" -w "$WORDLIST" -mc all > "$RUN/notes/calibration.txt"`.
3. **Directory fuzz:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" -- ffuf -u "$target" -w "$WORDLIST" -mc 200,301,302,401,403 -o "$RUN/ffuf.json" -of json`. Refine `-fc`/`-fs`/`-fw` from calibration.
4. **Variants (optional).** Parameter fuzz (`?FUZZ=1`); virtual-host discovery by fuzzing the `Host:` header with a vhost wordlist (same filter calibration).
5. **Extract:** `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" -- jq -r '.results[].url' "$RUN/ffuf.json" > "$RUN/found.txt"`. Summarize count or `no hits`; feed to vuln-class skills/Burp. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status complete --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'calibrated=ok:notes/calibration.txt' --item 'fuzz-ran=ok:findings.md' --target-state unchanged --cleanup not-needed`.

## Modern tooling & alternatives
`ffuf` and `feroxbuster` are the current standard; `gobuster` is still common. Legacy
`dirb` / `dirbuster` / `wfuzz` are superseded. Heavily wordlist-driven — pick by context (SecLists).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and every contacted host/vhost checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: calibrated
    desc: Filters calibrated against a known-bad baseline to suppress false positives
    verify: nonempty
    evidence: notes/calibration.txt
    on_fail: redo-part
    required: true
  - id: fuzz-ran
    desc: Fuzzing executed; run marker written (even if nothing found)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: paths-found
    desc: At least one path/param/vhost discovered (none is a valid outcome)
    verify: min-lines:1
    evidence: found.txt
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- **Always calibrate** filters against a known-bad response first — uncalibrated runs drown real hits in false positives.
- Pick the wordlist by context (raft/dir vs. extensions vs. params vs. vhosts); the wordlist, not the flags, drives results.
- Recursive/large wordlists can explode request volume — keep it bounded and honour rate limits.
- No hits still finishes with that summary. Vhost fuzzing needs authorization covering all candidate vhosts before contact.
