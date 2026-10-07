---
name: linpeas
description: >
  Use after an initial foothold to enumerate local privilege-escalation vectors on a compromised
  host with linpeas/winpeas (PEASS-ng) — SUID, capabilities, cron, creds, misconfigs, kernel —
  then turn red/yellow highlights into concrete abuse via GTFOBins/LOLBAS. Runs after a foothold
  skill; feeds the privesc exploit step. Not for remote/network enum (nmap/netexec).
arguments: "target transport [reviewed_peass_path]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: privesc-creds
domain: host
---

# linpeas / winpeas — automated privilege-escalation enumeration (PEASS-ng)

Shared contract: see AGENTS.md.

## Goal
Find one useful local privilege hypothesis from cheap context first; use PEASS only when justified.
Colored highlights are candidates, never verified privilege escalation.

## Steps
1. Identify proved foothold TARGET/transport. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill linpeas --target "$TARGET" --profile local-context --coverage-set 'Selected cheap local-context checks')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with known OS/access, hypothesis, <=240-second total task and PEASS trigger; record transport privately.
2. Reuse prior context, or one <=30-second helper-wrapped one-shot for `id; uname -a; pwd; ls -la ~`, with matching remote-native bounds. Inspect a selected known rule/path/version next only if it discriminates the hypothesis. No default filesystem-wide SUID/capability search, process watcher or kernel-exploit stage.
3. If cheap checks fail to discriminate and allocation permits, stage only a locally reviewed/versioned PEASS artifact at a unique remote path. No download-to-shell, default `-a`, remote tee/output file or automatic winPEAS ladder. Execute once with remote-native <=150-second bound and local `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 180 --grace 5 -- <verified one-shot transport argv>`; save actual output in evidence/peass.txt. Unsupported remote bounds -> do not launch; hard failure -> stop and disclose owed cleanup.
4. Cross-check <=3 relevant candidates against actual version/permission/path and GTFOBins/LOLBAS/CVE prerequisites. Record confirmed facts, rejected leads and unknowns in notes/vectors.md; no exploitation here. Save actual context/PEASS coverage, skips and artifact/cleanup state in notes/assessment.md; remove staged artifacts with positive exact-path absence proof only after normally ended commands.
5. Set PROFILE/COVERAGE to actual context-only or justified PEASS set. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --profile "$PROFILE" --coverage-set "$COVERAGE" --stop-reason "$STOP" --omitted 'Unselected enumeration and exploitation' --item 'scope-confirmed=ok:../../scope.json' --item 'enum-captured=ok:events.jsonl' --item 'vectors-analyzed=ok:notes/vectors.md' --item 'results-recorded=ok:notes/assessment.md'`; include only verified facts/findings with actual state/artifacts/cleanup. Completed selected checks can be negative; native unfinished is partial, helper failure error. Return candidates to coordinator, never start privesc-root.

## Modern tooling & alternatives
PEASS-ng: `linpeas.sh` (Linux), `winPEASx64.exe` (Windows). Companions: `pspy` (watch cron/processes
without root), `linux-exploit-suggester` / `wesng` (kernel/OS → known exploits). AD post-ex: `mimikatz` / `impacket secretsdump`.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and foothold host checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: enum-captured
    desc: Actual events/context or conditional PEASS output substantiate selected enumeration
    verify: judge
    evidence: events.jsonl
    on_fail: fail
    required: true
  - id: vectors-analyzed
    desc: Highlights cross-checked against GTFOBins/LOLBAS/CVEs; candidates recorded (or "none")
    verify: judge
    evidence: notes/vectors.md
    on_fail: redo-part
    required: true
  - id: results-recorded
    desc: Actual coverage, omitted checks and exact artifact/cleanup state evidenced
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Noisy / slow** — fine in labs, think twice in sensitive environments; `scope-confirmed` fails hard (`on_fail: fail`).
- **Don't blindly run suggested exploits** — verify each vector (version, writability, path) first; kernel exploits can crash the host.
- Triage red/yellow highlights, not the whole dump — then map to a concrete GTFOBins/LOLBAS command. `pspy` catches root cron/processes a one-shot run can miss.
- No vector still records `none` in notes/vectors.md and finishes with the matching summary.
