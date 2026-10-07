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
agent: recon-runner
background: false
category: recon
domain: web
---

# ffuf — web fuzzer (dirs, files, params, vhosts)

Shared contract: see AGENTS.md.

## Goal
Test one content-discovery hypothesis with calibrated low-load batches. Produce verified candidate
URLs and truthful processed/unprocessed coverage, not default-page or dotfile-403 findings.

## Steps
1. Map known pages first; put one `FUZZ` in `target` and select a contextual WORDLIST. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ffuf --target "$target" --profile pilot --coverage-set 'At most 100 contextual entries, 15 native seconds')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$target" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, input count, total allocation, positive controls and expansion trigger; validate installed ffuf/help.
2. Save three distinct invalid-path controls (status, location, headers/body and size). For each CONTROL, `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" --timeout 10 -- curl --connect-timeout 3 --max-time 5 -sS -D "$RUN/evidence/control-$CONTROL.headers" -o "$RUN/evidence/control-$CONTROL.body" -w '%{http_code} %{size_download} %{redirect_url}\n' "${target/FUZZ/otus-invalid-$CONTROL}"`; never follow unchecked redirects. Describe comparisons/filters in notes/calibration.md; optional `-ac` must not filter known positives.
3. Save at most 100 actual entries to notes/pilot.txt. Pilot: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" --timeout 35 --grace 5 -- ffuf -u "$target" -w "$RUN/notes/pilot.txt" -t 5 -rate 10 -timeout 3 -maxtime 15 -noninteractive -se -mc all -o "$RUN/evidence/pilot.json" -of json`. Apply only justified `-fc/-fs/-fw` filters; no recursion or extension multiplication.
4. Inspect native JSON/log and health BEFORE another batch. Record attempted/processed/errors, native stop and useful non-baseline hits in notes/coverage.md; unavailable metrics stay unknown. A normally ended healthy pilot with a useful lead may justify at most 400 additional entries and `-maxtime 45`, helper `--timeout 65`, otherwise stop. Preserve followup.json separately; total initial native fuzz <=60 seconds. A health stop is partial, not a negative or permission to raise load.
5. Validate retained hits with <=3 bounded control comparisons; keep requests/responses. Extract clean candidate URLs from native JSON with `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- jq -r '.results[].url' "$RUN/evidence/pilot.json" > "$RUN/found.txt"`; include a separate successful followup only if it actually ran. Empty found.txt is valid, never write a no-hit marker into JSON/list files.
6. Larger lists/parameters/vhosts need a new finite task and lead; all candidate vhosts and transport endpoints must be checked BEFORE contact. Set PROFILE/COVERAGE to actual pilot-only or pilot-plus-followup entry/time sets, never leave expanded work labeled 100/15. Native budget/unprocessed entries -> partial/native-budget, completed declared batch -> complete/completed; helper nonzero -> error, stop. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --profile "$PROFILE" --coverage-set "$COVERAGE" --stop-reason "$STOP" --omitted 'Untested entries, recursion and other fuzz modes' --item 'scope-confirmed=ok:../../scope.json' --item 'calibrated=ok:notes/calibration.md' --item 'fuzz-ran=ok:events.jsonl' --item 'coverage-assessed=ok:notes/coverage.md' --target-state unchanged --cleanup not-needed`; use fail items for unsupported assertions. Return candidates/proposal, not a chained scan.

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
    desc: Three real controls and known positives substantiate filters and candidate triage
    verify: judge
    evidence: notes/calibration.md
    on_fail: redo-part
    required: true
  - id: fuzz-ran
    desc: Paired events and unchanged native JSON/log prove the bounded attempt and exit
    verify: judge
    evidence: events.jsonl
    on_fail: redo-skill
    required: true
  - id: coverage-assessed
    desc: Counts, errors, omissions and native budget or health stop match raw evidence
    verify: judge
    evidence: notes/coverage.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- `-se` stops spurious/consecutive errors; it is NOT an aggregate error-rate threshold.
- Native `-maxtime` may flush JSON with incomplete coverage; helper expiry is still error.
- A 403, redirect or default-page match alone is not a vulnerability. Avoid repeated known noise.
