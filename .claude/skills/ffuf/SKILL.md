---
name: ffuf
description: >
  Use when fuzzing a web target for hidden directories, files, parameters, or virtual
  hosts — content discovery / directory brute-forcing with ffuf. Wordlist-driven; its
  hits feed LFI/upload/IDOR and manual/Burp testing. Not for subdomain discovery
  (use subfinder) or template-based vuln scanning (use nuclei).
arguments: "target_url wordlist [output]"
model: inherit
effort: medium
context: fork
agent: general-purpose
---

# ffuf — web fuzzer (dirs, files, params, vhosts)

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if the web target is not confirmed in scope.

Run via the `recon-runner` subagent.

## Goal (desired outcome)
Discover hidden paths, files, parameters, and virtual hosts on an in-scope web target, producing
a calibrated, low-false-positive list of hits to drive manual and vuln-class testing.

## Steps
1. **Precondition / scope / wordlist.** Confirm the target is in scope and pick a wordlist by
   context (see §7 shared SecLists). Anchor a timestamped run directory to the repo root (never
   write under `skills/`). `target_url` must contain the `FUZZ` keyword at the fuzz position:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/ffuf/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   target="${1:?target_url with FUZZ keyword required}"   # e.g. https://t/FUZZ
   WORDLIST="${2:?wordlist path required}"
   echo "target=$target confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
2. **Calibrate filters.** Probe a known-bad path to learn the baseline response (status / size /
   words) so filters kill false positives, and record it for the reviewer:
   ```bash
   ffuf -u "${target/FUZZ/ffuf-calibrate-$RANDOM}" -w "$WORDLIST" -mc all 2>&1 \
     | tee "$RUN/notes/calibration.txt" >> "$RUN/run.log"
   ```
3. **Directory fuzz**, keeping interesting status codes and saving JSON:
   ```bash
   ffuf -u "$target" -w "$WORDLIST" -mc 200,301,302,401,403 -o "$RUN/ffuf.json" -of json | tee -a "$RUN/run.log"
   ```
   Then refine with filters derived from calibration: `-fc <codes>` / `-fs <size>` / `-fw <words>`.
4. **Variants (optional).** Parameter fuzz: `ffuf -u "https://host/page?FUZZ=1" -w "$WORDLIST" ...`.
   Virtual-host discovery: fuzz the `Host:` header with a vhost wordlist (same filter calibration).
5. **Extract hits + marker.** Pull the discovered URLs and always write a run marker:
   ```bash
   jq -r '.results[].url' "$RUN/ffuf.json" 2>/dev/null > "$RUN/found.txt" || : > "$RUN/found.txt"
   count="$(wc -l < "$RUN/found.txt" | tr -d ' ')"
   if [ "$count" -gt 0 ]; then echo "ffuf: $count hits on $target" > "$RUN/summary.txt";
   else echo "no hits" > "$RUN/summary.txt"; fi
   ```
   Feed `found.txt` to vuln-class skills (LFI, upload, IDOR) / Burp, then write `_run.json`.

Hand the run dir to the `reviewer` subagent to verify before treating results as final.

## Modern tooling & alternatives
`ffuf` and `feroxbuster` are the current standard; `gobuster` is still common. Legacy
`dirb` / `dirbuster` / `wfuzz` are superseded.

## Output formats
`-of json|csv|html|md` (default is stdout). Save the machine-readable run to `$RUN/ffuf.json`, the
extracted hits to `$RUN/found.txt`, plus a run record `$RUN/_run.json`:
```json
{
  "skill": "ffuf",
  "target": "<target_url>",
  "run_dir": "out/ffuf/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed": { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "calibrated":      { "attempted": true, "ok": true, "evidence": "notes/calibration.txt" },
    "fuzz-ran":        { "attempted": true, "ok": true, "evidence": "summary.txt", "exit": 0 },
    "paths-found":     { "attempted": true, "ok": true, "evidence": "found.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (ffuf missing, target unreachable,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Heavily wordlist-driven** — see §7 on shared wordlists (SecLists) under `_shared/wordlists/`. A
"which wordlist for which context" RAG note is high-value. Consumes a live URL from `httpx`; feeds
vuln-class skills (LFI, upload, IDOR) and Burp.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Web target confirmed in scope before fuzzing
    verify: judge
    evidence: notes/scope.txt
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
    evidence: summary.txt
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
- **Always calibrate** filters against a known-bad response first — uncalibrated runs drown real
  hits in false positives.
- Pick the wordlist by context (raft/dir vs. extensions vs. params vs. vhosts); the wordlist, not
  the flags, drives results.
- Recursive/large wordlists can explode request volume — keep it bounded and honour rate limits.
- A run that finds nothing must still write `summary.txt` ("no hits") so "ran but empty" ≠
  "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/ffuf/<timestamp>/` (git-ignored).
