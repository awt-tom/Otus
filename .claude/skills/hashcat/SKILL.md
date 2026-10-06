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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Identify the hash type with `hashid`/`name-that-hash` → a hashcat `-m <mode>` (record it in `notes/mode.txt`); fail fast on an empty hash file. Default `WL=/usr/share/wordlists/rockyou.txt`.
2. **Wordlist attack** (fastest first pass): `hashcat -m "$MODE" "$HASHES" "$WL" --outfile "$RUN/cracked.txt" 2>&1 | tee -a "$RUN/run.log"`.
3. **Escalate deliberately** (don't brute blindly): add rules `-r /usr/share/hashcat/rules/best64.rule`, then a mask `-a 3 '?u?l?l?l?l?d'` — same `-m`/`--outfile`.
4. **List cracked + marker + run record.** `hashcat -m "$MODE" "$HASHES" --show > "$RUN/show.txt"` lists everything cracked (from the potfile). Write a run marker (`no hashes cracked` if none), then `run.json`. Feed cracked creds to `netexec`/login skills.

## Modern tooling & alternatives
`hashcat` (GPU) is primary; `john` (Jumbo) for format coverage / CPU and `*2john` converters (zip2john,
ssh2john, …) bridge formats. `hashid`/`name-that-hash` for identification. Keep a wordlist + rules ladder rather than brute-forcing blindly.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); hashes and use of recovered creds in scope
    verify: judge
    evidence: ../../scope.txt
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
- `*2john`/jumbo converters bridge archive/doc formats into crackable hashes. A run that cracks nothing still writes `findings.md` ("no hashes cracked").
