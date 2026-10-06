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
effort: medium
context: inline
agent:
category: privesc-creds
domain: crypto
---

# hashcat — GPU password/hash cracking

Shared contract: see AGENTS.md.

## Goal
Recover plaintext from captured hashes — identify the hash type, crack with an escalating
wordlist → rules → mask strategy, and list what cracked — to enable authenticated access or lateral movement.

## Steps
1. Offline work: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill hashcat)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Helper-wrap hashid/name-that-hash; record `MODE` in `notes/mode.txt`. Empty hashes finalize error. Default `WL=/usr/share/wordlists/rockyou.txt`.
2. `python3 -I scripts/otus-log.py run --run-dir "$RUN" -- hashcat -m "$MODE" "$HASHES" "$WL" --outfile "$RUN/cracked.txt"`. Arguments remain unchanged; metadata is redacted, raw output stays restricted.
3. **Escalate deliberately** (don't brute blindly): add rules `-r /usr/share/hashcat/rules/best64.rule`, then a mask `-a 3 '?u?l?l?l?l?d'` — same `-m`/`--outfile`.
4. Every subsequent hashcat call uses the helper, including `hashcat -m "$MODE" "$HASHES" --show > "$RUN/show.txt"`; do not include unrelated potfile entries. Nonzero exhaustion is recorded with its actual exit and explained, not silently promoted. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'mode-identified=ok:notes/mode.txt' --item 'crack-attempted=ok:findings.md' --target-state unchanged --cleanup not-needed`; use no-hashes summary or secret-free verified findings. Credential reuse requires a separate endpoint check.

## Modern tooling & alternatives
`hashcat` (GPU) is primary; `john` (Jumbo) for format coverage / CPU and `*2john` converters (zip2john,
ssh2john, …) bridge formats. `hashid`/`name-that-hash` for identification. Keep a wordlist + rules ladder rather than brute-forcing blindly.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and artifact provenance checked; reuse gated separately
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: mode-identified
    desc: Hash type identified and mapped to a hashcat -m mode
    verify: nonempty
    evidence: notes/mode.txt
    on_fail: redo-part
    required: true
  - id: crack-attempted
    desc: Cracking executed (wordlist→rules→mask ladder); run marker written
    verify: nonempty
    evidence: findings.md
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
- **Don't brute blindly** — climb the ladder (wordlist → rules → masks → combinator); most cracks come from `rockyou` + `best64.rule`.
- Pick `-m <mode>` from the hash type first; a wrong mode wastes the whole run. The potfile caches results — `--show` re-lists cracked hashes instantly without re-cracking.
- `*2john`/jumbo converters bridge formats. No recovered hashes still finishes with an explicit secret-free summary.
