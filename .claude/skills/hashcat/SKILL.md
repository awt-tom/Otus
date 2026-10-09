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
context: fork
agent: vuln-hunter
background: false
category: privesc-creds
domain: crypto
---

# hashcat — GPU password/hash cracking

Shared contract: see AGENTS.md.

## Goal
Test one context-supported offline hash hypothesis with isolated output and truthful exhaustion,
native-budget and recovery counts. Wordlist/rule/mask attacks are alternatives, not a default ladder.

## Steps
1. Offline work: `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill hashcat --profile selected-wordlist --coverage-set 'Selected contextual dictionary and 60 native seconds')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --run-dir "$RUN"`; nonzero STOP. Verify nonempty HASHES/provenance/mode from source format, not one heuristic. Write notes/task.md with input count, supported binary/backend, hypothesis and <=120-second initial allocation; record MODE/version/backend and exact candidate set in notes/mode.txt.
2. Verify installed version/backend before cracking; no `--force` or silent fallback. Choose a finite context-supported WL, not default rockyou/rules/mask expansion. Set POLICY=hashcat-v6.2.6 only for verified v6.2.6 with this direct cracking argv; other versions remain strict until separately source-verified, never arbitrary allowed exits. SESSION is a unique nonsecret run name; pot/restore/outfile paths are per-run.
3. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 90 --grace 5 --outcome-policy "$POLICY" -- hashcat -m "$MODE" -a 0 "$HASHES" "$WL" --runtime 60 --status --status-json --session "$SESSION" --restore-file-path "$RUN/loot/hashcat.restore" --potfile-path "$RUN/loot/hashcat.pot" --outfile "$RUN/loot/cracked.txt"`. No wrapper/special-mode policy, quiet banner suppression or automatic attack ladder. Hard failure stops.
4. Inspect final native JSON/actual tool exit and helper execution metadata. Handled exit 1/status 5 is exhausted selected work (possibly with recovered hashes); exit 4/status 11 is native-budget partial, not exhaustion/negative. Deadline/unsupported/missing/contradictory evidence remains error. Only after a normally handled command: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- hashcat -m "$MODE" "$HASHES" --potfile-path "$RUN/loot/hashcat.pot" --show > "$RUN/loot/show.txt"`; this input/pot only, no unrelated recovered credentials.
5. Save tested/unprocessed coverage, actual recovered count and outcome in notes/assessment.md, no plaintext. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected candidates, rules and masks' --item 'scope-confirmed=ok:../../scope.json' --item 'mode-identified=ok:notes/mode.txt' --item 'crack-attempted=ok:events.jsonl' --target-state unchanged --cleanup not-needed`; complete only a finished selected attack, native-budget stays partial. Add only input-backed secret-free findings; another attack/reuse needs a new hypothesis/allocation and separate endpoint gate.

## Modern tooling & alternatives
`hashcat` (GPU) is primary; `john` (Jumbo) for format coverage / CPU and `*2john` converters (zip2john,
ssh2john, …) bridge formats. Heuristic mode guesses need source-format confirmation.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and artifact provenance checked; reuse gated separately
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: mode-identified
    desc: Provenance, actual format/mode, version/backend and candidate set checked
    verify: judge
    evidence: notes/mode.txt
    on_fail: redo-part
    required: true
  - id: crack-attempted
    desc: Events/native final JSON prove the selected attack, signed exit and actual outcome
    verify: judge
    evidence: events.jsonl
    on_fail: fail
    required: true
  - id: cracked-recorded
    desc: Any recovered count matches this input and isolated pot/show proof, no unrelated entries
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: false
```

## Notes / pitfalls
- Reuse reviewed unchanged attack results; exhaustion can contain recovered hashes and never proves a password absent from all candidates.
- Strict unsupported-version exits are errors, not silently promoted native budgets; preserve actual child exit.
- `*2john`/jumbo converters bridge formats. No recovered hashes still finishes with an explicit secret-free summary.
