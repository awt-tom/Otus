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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Pick a wordlist by context; `target_url` must contain the `FUZZ` keyword at the fuzz position (e.g. `https://t/FUZZ`).
2. **Calibrate filters** — probe a known-bad path to learn the baseline (status/size/words) and record it: `ffuf -u "${target/FUZZ/ffuf-calibrate-$RANDOM}" -w "$WORDLIST" -mc all 2>&1 | tee "$RUN/notes/calibration.txt" >> "$RUN/run.log"`.
3. **Directory fuzz**, keeping interesting codes and saving JSON: `ffuf -u "$target" -w "$WORDLIST" -mc 200,301,302,401,403 -o "$RUN/ffuf.json" -of json | tee -a "$RUN/run.log"`. Refine with `-fc`/`-fs`/`-fw` from calibration.
4. **Variants (optional).** Parameter fuzz (`?FUZZ=1`); virtual-host discovery by fuzzing the `Host:` header with a vhost wordlist (same filter calibration).
5. **Extract hits + marker.** `jq -r '.results[].url' "$RUN/ffuf.json" > "$RUN/found.txt"`; if empty write `no hits` to `findings.md`, else summarize. Feed `found.txt` to vuln-class skills (LFI, upload, IDOR)/Burp. Write `run.json`.

## Modern tooling & alternatives
`ffuf` and `feroxbuster` are the current standard; `gobuster` is still common. Legacy
`dirb` / `dirbuster` / `wfuzz` are superseded. Heavily wordlist-driven — pick by context (SecLists).

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
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
- A run that finds nothing must still write `findings.md` ("no hits").
