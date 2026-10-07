---
name: impacket
description: >
  Use for AD/Windows protocol actions with the Impacket example scripts once you have creds or
  hashes (often from netexec) — RCE (psexec/wmiexec), credential dumping (secretsdump, incl. DCSync
  -just-dc), Kerberoast (GetUserSPNs -request), AS-REP roast (GetNPUsers -request), NTLM relay
  (ntlmrelayx). Feeds hashes to hashcat. Not for attack-path mapping (bloodhound) or web (burpsuite).
arguments: "action target [-u user] [-p pass] [-hashes LM:NT] [-dc-ip ip]"
model: inherit
effort: medium
context: fork
agent: vuln-hunter
background: false
category: ad-network
domain: ad
---

# impacket — AD/Windows protocol tools (psexec · secretsdump · GetUserSPNs · ntlmrelayx)

Shared contract: see AGENTS.md.

## Goal
Perform one least-destructive AD/Windows protocol action with supplied access and concrete proof.
Credential dumping, roasting, relay and RCE are alternatives, never a compulsory chain.

## Steps
1. Choose ONE goal-relevant action and supplied identity/hash/ticket; extract actual endpoints from credential-qualified argv into plain HOSTS, including DC/induced targets. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill impacket --profile selected-action --coverage-set 'One selected protocol action with supplied identity')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with hypothesis, installed script/version, finite task and <=60-second command cap; no secrets in metadata.
2. Inspect supported noninteractive argv/effects before contact; complete supplied auth avoids a password prompt. All actions use `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" --timeout 60 --grace 5 -- <verified one-shot argv>`. For a selected exec hypothesis, explicit `wmiexec.py "$IDENTITY" 'whoami'` is a one-shot alternative to a bare login; native remote bounds and actual cleanup effects must be established first. No bounded one-shot support -> partial/no launch.
3. Enumeration/roasting/minimal credential read require their own objective-relevant hypothesis and checked rights. No mandatory full secretsdump/DCSync, all-user roast or protocol ladder; select the least data necessary with version-supported filters. Every contacted endpoint stays checked. No held relay/listener or interactive shell; a local cap does not prove a remote process stopped.
4. Preserve actual per-run native loot/output and record artifact refs, proof, coverage, unmet prerequisites and created services/files in notes/results.md. Do not import unrelated caches. RCE/credentials require real evidence, not a command-success banner. Hard failure/refusal stops with unknown/owed cleanup as appropriate; no actionful retry.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Other protocol actions and broad credential extraction' --item 'scope-confirmed=ok:../../scope.json' --item 'action-executed=ok:events.jsonl' --item 'results-recorded=ok:notes/results.md'`; finished declared query can be scoped-negative complete, missing goal proof/unfinished partial, nonzero error. Add only secret-free verified findings with actual state/artifacts/cleanup; return next-task proposal to coordinator.

## Modern tooling & alternatives
Script aliases vary (`psexec.py` or `impacket-psexec`); verify installed versions during setup.
Use the smallest relevant protocol action, not every credential-capable tool.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization, every endpoint, and credential/hash use checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: action-executed
    desc: Paired events/native output substantiate the selected action or disclosed no-launch
    verify: judge
    evidence: events.jsonl
    on_fail: fail
    required: true
  - id: loot-captured
    desc: Artifacts (secrets/tickets/roast hashes) saved under loot/ via -outputfile
    verify: judge
    evidence: notes/results.md
    on_fail: fail
    required: false
  - id: results-recorded
    desc: Actual proof, coverage, omissions and exact artifact/cleanup state match evidence
    verify: judge
    evidence: notes/results.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- Target format `[[domain/]username[:password]@]<target>`; pass-the-hash uses `-hashes LMHASH:NTHASH` (omit password); `-k`/`-no-pass` for Kerberos.
- `secretsdump -just-dc` is **DCSync** — needs replication rights, high-signal; dump the minimum. Request roast hashes with `-format hashcat` so they drop into `hashcat`.
- psexec creates a service: capture cleanup proof. No captured artifacts still finishes with an explicit summary.
