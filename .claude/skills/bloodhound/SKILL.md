---
name: bloodhound
description: >
  Use when mapping Active Directory privilege-escalation / lateral-movement paths with
  BloodHound CE — collect AD objects (bloodhound-python / SharpHound / nxc --bloodhound),
  import, and run Cypher queries to find the shortest path to high-value targets (e.g. Domain
  Admin) and abusable ACLs. Consumes creds from netexec; feeds impacket/certipy. Not for
  credential spraying (netexec) or exploitation (metasploit/impacket).
arguments: "domain -u user -p pass -ns dc_ip"
model: inherit
effort: medium
context: inline
agent:
category: ad-network
domain: ad
---

# bloodhound — AD attack-path analysis (BloodHound CE)

Shared contract: see AGENTS.md.

## Goal
Collect AD objects and reveal privesc / lateral-movement paths to high-value targets (e.g. Domain
Admin) via Cypher — shortest path + abusable ACLs; re-collect as each new identity is gained.

## Steps
1. Gather creds/DC and a plain `HOSTS` list covering all contacted domain hosts. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill bloodhound)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. `mkdir -p "$RUN/collection"`; stop if collection would discover/contact unchecked hosts.
2. **Collect:** wrap `cd "$RUN/collection" && bloodhound-python -u <user> -p <pass> -d "$DOMAIN" -c All -ns <DC_IP>` with `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" -- bash -o pipefail -c '<command>'`; export required variables. SharpHound / `nxc ldap <DC> -u u -p p --bloodhound` use the same checked wrapper.
3. **Import** the resulting JSON/zip into **BloodHound CE** (drag-drop / API upload).
4. **Analyse:** save Cypher queries and observed attack paths/ACLs in `notes/paths.md`; GUI import/query steps write helper marker events. No inferred path is a proved exploit.
5. Re-collection with a new identity gets a fresh isolated run. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'collected=ok:collection' --item 'paths-analyzed=ok:findings.md' --item 'results-recorded=ok:findings.md'`; add verified `--finding` entries referencing query evidence, or no-path summary, with actual state/cleanup.

## Modern tooling & alternatives
BloodHound **CE** is current — match the collector to the CE ingest version. Collectors: `bloodhound-python`
(remote), `SharpHound` (on a host), `nxc ldap --bloodhound`. Keep a Cypher query library in RAG.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and all collection hosts checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: collected
    desc: AD collection produced into the run directory (JSON/zip)
    verify: exists
    evidence: collection
    on_fail: redo-part
    required: true
  - id: paths-analyzed
    desc: Cypher queries run; attack paths / abusable ACLs recorded (or documented "none")
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: results-recorded
    desc: Run marker written (even when no path identified)
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Collection is noisy** — scope it to the lab; `scope-confirmed` fails hard (`on_fail: fail`).
- **Match the collector version to the BloodHound CE ingest version**, or import fails / misparses.
- **Re-collect as each new identity is gained** — paths change with new group membership.
- Feeds impacket/certipy and offline hashcat. No path still finishes with a no-path summary.
