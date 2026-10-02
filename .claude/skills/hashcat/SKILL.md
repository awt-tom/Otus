---
name: hashcat
description: >
  Use when cracking captured password hashes with hashcat (GPU) to recover plaintext for auth /
  lateral movement — identify the hash type, map to -m <mode>, run wordlist → rules → mask
  attacks, and list cracked with --show. Consumes hashes from secretsdump/responder/web dumps
  (incl. Kerberoast/AS-REP from impacket); feeds netexec/login skills. Not for online login
  brute (use hydra).
arguments: "hashes_file [mode] [wordlist]"
model: inherit
effort: high
context: inline
agent:
---

# hashcat — GPU password/hash cracking

**Scope guard:** Authorized work only (in-scope program / lab / owned). Only crack hashes you are authorized to possess and use; cracked credentials are used only against in-scope systems. Abort if the hashes or their use are not in scope.

## Goal (desired outcome)
Recover plaintext from captured hashes — identifying the hash type, cracking with an escalating
wordlist → rules → mask strategy, and listing what cracked — to enable authenticated access or
lateral movement, with cracked creds recorded for the report.

## Steps
1. **Precondition / scope / identify.** Confirm the hashes are in scope. Identify the hash type with
   `hashid` / `name-that-hash` and map it to a hashcat `-m <mode>`. Anchor a timestamped run
   directory to the repo root (never write under `skills/`); fail fast on an empty hash file:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/hashcat/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/notes"
   HASHES="${1:?path to hashes file required}"; MODE="${2:?hashcat -m mode required}"; WL="${3:-/usr/share/wordlists/rockyou.txt}"
   [ -s "$HASHES" ] || { echo "hash file empty/missing: $HASHES" | tee -a "$RUN/run.log"; exit 1; }
   echo "hashes confirmed in scope; mode=$MODE: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
2. **Wordlist attack** (straight) — fastest first pass:
   ```bash
   hashcat -m "$MODE" "$HASHES" "$WL" --outfile "$RUN/cracked.txt" 2>&1 | tee -a "$RUN/run.log"
   ```
3. **Escalate deliberately** (don't brute blindly) — climb the strategy ladder:
   ```bash
   hashcat -m "$MODE" "$HASHES" "$WL" -r /usr/share/hashcat/rules/best64.rule --outfile "$RUN/cracked.txt" 2>&1 | tee -a "$RUN/run.log"
   hashcat -m "$MODE" "$HASHES" -a 3 '?u?l?l?l?l?d' --outfile "$RUN/cracked.txt" 2>&1 | tee -a "$RUN/run.log"   # mask
   ```
4. **List cracked + marker.** `--show` lists everything cracked (from the potfile); always write a
   run marker so "ran but nothing" ≠ "didn't run":
   ```bash
   hashcat -m "$MODE" "$HASHES" --show > "$RUN/show.txt" 2>>"$RUN/run.log" || true
   if [ -s "$RUN/cracked.txt" ] || [ -s "$RUN/show.txt" ]; then
     echo "hashcat: $(wc -l < "$RUN/cracked.txt" 2>/dev/null || echo 0) cracked (see cracked.txt / show.txt)" > "$RUN/summary.txt"
   else
     echo "no hashes cracked" > "$RUN/summary.txt"
   fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats). Feed cracked creds
   to `netexec` / login skills.

## Modern tooling & alternatives
`hashcat` (GPU) is primary; `john` (Jumbo) for format coverage / CPU and `*2john` converters that
bridge many formats (zip2john, ssh2john, …). `hashid` / `name-that-hash` for identification. Keep a
wordlist + rules strategy ladder rather than brute-forcing blindly.

## Output formats
Potfile at `~/.hashcat/hashcat.potfile` (global cracked store); `--outfile` writes cracked
hash:plain to `$RUN/cracked.txt`; `--show` lists cracked to `$RUN/show.txt`. This skill also writes
`$RUN/summary.txt` (run marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "hashcat",
  "target": "<hashes_file>",
  "run_dir": "out/hashcat/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "mode-identified":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "crack-attempted":  { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "cracked-recorded": { "attempted": true, "ok": true, "evidence": "cracked.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (hashcat missing, bad mode, empty input,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**High RAG value:** a hash-mode lookup table (`-m` per hash type) + rules/mask cheat-sheet. Consumes
hashes from `impacket` (`secretsdump`, Kerberoast/AS-REP), `responder`, and web dumps; cracked creds
feed `netexec` and login skills. Shares the wordlist pool (rockyou/SecLists) — see §7.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Hashes (and use of recovered creds) confirmed in scope before cracking
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: mode-identified
    desc: Hash type identified and mapped to a hashcat -m mode
    verify: nonempty
    evidence: notes/scope.txt
    on_fail: redo-part
    required: true
  - id: crack-attempted
    desc: Cracking executed (wordlist→rules→mask ladder); run marker written
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: cracked-recorded
    desc: Cracked hash:plain recorded (or documented "none cracked")
    verify: exists
    evidence: cracked.txt
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- **Don't brute blindly** — climb the ladder (wordlist → rules → masks → combinator); most cracks
  come from `rockyou` + `best64.rule`.
- Pick `-m <mode>` from the hash type first; a wrong mode wastes the whole run.
- The potfile caches results — `--show` re-lists cracked hashes instantly without re-cracking.
- `*2john` / jumbo converters bridge archive/doc formats into crackable hashes.
- A run that cracks nothing must still write `summary.txt` ("no hashes cracked") so "ran but empty"
  ≠ "didn't run".
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/hashcat/<timestamp>/` (git-ignored).
