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
1. Set up the run dir per AGENTS.md (`$RUN`, `mkdir -p "$RUN/collection" "$RUN/notes"`); scope inherited from `out/<engagement>/scope.txt`. **Collection is noisy — scope it to the lab.** Gather valid creds (often from `netexec`) and the DC IP (`-ns`).
2. **Collect** into the collection dir (match collector to the CE ingest version): `cd "$RUN/collection" && bloodhound-python -u <user> -p <pass> -d "$DOMAIN" -c All -ns <DC_IP> 2>&1 | tee -a "$RUN/run.log"`. Alternatives: SharpHound on a domain host, or `nxc ldap <DC> -u u -p p --bloodhound`.
3. **Import** the resulting JSON/zip into **BloodHound CE** (drag-drop / API upload).
4. **Analyse with Cypher.** Run built-in + custom queries (kerberoastable, DCSync rights, shortest path to Domain Admins, abusable ACLs). Record each attack path / abusable ACL with the query used in `findings.md`.
5. **Marker + re-collect loop + run record.** Write a run marker (`- none …` if no path), then re-collect as each new identity is gained. Write `run.json`.

## Modern tooling & alternatives
BloodHound **CE** is current — match the collector to the CE ingest version. Collectors: `bloodhound-python`
(remote), `SharpHound` (on a host), `nxc ldap --bloodhound`. Keep a Cypher query library in RAG.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed); collection scoped to the lab
    verify: judge
    evidence: ../../scope.txt
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
- Feeds `impacket`/`certipy`; kerberoast/AS-REP hashes feed `hashcat`. A run that finds no path still writes a `- none` line in `findings.md`.
