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
context: fork
agent: vuln-hunter
background: false
category: ad-network
domain: ad
---

# bloodhound — AD attack-path analysis (BloodHound CE)

Shared contract: see AGENTS.md.

## Goal
Answer one AD path/ACL hypothesis with targeted compatible collection and actual import/query proof.
A graph edge/path is a candidate, not verified exploitation.

## Steps
1. Select one hypothesis/method set, supplied identity/DC and plain HOSTS covering actual DNS/DC/GC endpoints. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill bloodhound --profile targeted-ad --coverage-set 'Selected directory methods and one graph hypothesis')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --targets-file "$HOSTS" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with collector/CE compatibility, actual method set, <=180-second collection cap/finite total allocation; create collection/.
2. Verify installed collector flags/ingest version before contact. Example directory-only hypothesis: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --targets-file "$HOSTS" --timeout 180 --grace 5 -- bash -o pipefail -c 'cd "$1" && shift && exec "$@"' otus-bloodhound "$RUN/collection" "$COLLECTOR" -u "$USER" -p "$PASS" -d "$DOMAIN" -c Group,ACL -dc "$DC_HOST" -gc "$DC_HOST" -ns "$DC_IP"`. Use only a supported compatible binary and validated endpoint overrides; no default All/computer sessions/unchecked host discovery. If the collector cannot constrain contacts, do not launch.
3. Verify actual nonempty native files/object counts, not collection/ existence; preserve files unchanged. Import only this collection to compatible CE and save real import receipt/log or GUI export. Missing CE/import capability -> partial, not an invented import. Manual steps use marker events plus actual evidence; CLI import/query is checked and capped to remaining allocation.
4. Save actual Cypher text, result exports/screenshots and source-object refs in notes/paths.md. Reuse reviewed unchanged collection; recollect only after a recorded relevant membership/permission/endpoint change. No automatic recollection for every identity or execution of a graph path.
5. Record actual collected/imported/queried coverage and omissions in notes/assessment.md. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected directory methods and host sessions' --item 'scope-confirmed=ok:../../scope.json' --item 'collected=ok:notes/assessment.md' --item 'paths-analyzed=ok:notes/paths.md' --item 'results-recorded=ok:notes/assessment.md'`; selected imported/query task finished -> complete even no path; native unfinished/missing import -> partial, helper failure error. Include real findings/state/cleanup; return candidate paths to coordinator.

## Modern tooling & alternatives
BloodHound **CE** is current — match the collector to the CE ingest version. Collectors: `bloodhound-python`
(remote), `SharpHound` (on a host), `nxc ldap --bloodhound`. Keep a Cypher query library in RAG.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and all collection hosts checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: collected
    desc: Native objects/files plus actual compatible import receipt substantiate selected collection
    verify: judge
    evidence: notes/assessment.md
    on_fail: redo-part
    required: true
  - id: paths-analyzed
    desc: Actual queries/results support paths or scoped no-path result; unavailable work disclosed
    verify: judge
    evidence: notes/paths.md
    on_fail: fail
    required: true
  - id: results-recorded
    desc: Actual collection/import/query coverage, skips and stops match native evidence
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Collection is noisy** — scope it to the lab; `scope-confirmed` fails hard (`on_fail: fail`).
- **Match the collector version to the BloodHound CE ingest version**, or import fails / misparses.
- Record relevant changes before recollection; new identity alone does not prove old graph data changed.
- Feeds impacket/certipy and offline hashcat. No path still finishes with a no-path summary.
