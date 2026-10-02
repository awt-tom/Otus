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
effort: high
context: inline
agent:
---

# bloodhound — AD attack-path analysis (BloodHound CE)

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Confirm the target domain is in scope and **scope collection to the lab** — SharpHound/bloodhound-python collection is noisy. Abort if the domain is not confirmed in scope.

## Goal (desired outcome)
Collect AD objects and reveal privilege-escalation / lateral-movement paths to high-value targets
(e.g. Domain Admin) — identifying the shortest path and abusable ACLs via Cypher — and re-collect
as each new identity is gained, since paths change.

## Steps
1. **Precondition / scope / inputs.** Confirm the domain is in scope and gather valid creds (often
   from `netexec`) and the DC IP (`-ns`). Anchor a timestamped run directory to the repo root
   (never write under `skills/`); collect *into* it so artifacts are self-contained:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_bloodhound="${OTUS_RUN_DIR:-$ROOT/out/bloodhound/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_bloodhound"
   mkdir -p "$RUN/collection" "$RUN/notes"
   DOMAIN="${1:?domain required}"
   echo "domain $DOMAIN confirmed in scope; collection scoped to lab: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/findings.md"
   ```
2. **Collect.** Run a collector into the collection dir (match collector version to the BloodHound
   CE ingest version):
   ```bash
   cd "$RUN/collection"
   bloodhound-python -u <user> -p <pass> -d "$DOMAIN" -c All -ns <DC_IP> 2>&1 | tee -a "$RUN/run.log"
   # alternatives: SharpHound on a domain host, or: nxc ldap <DC> -u u -p p --bloodhound
   ```
3. **Import.** Load the resulting JSON/zip into **BloodHound CE** (drag-drop / API upload).
4. **Analyse with Cypher.** Run built-in and custom Cypher queries (kerberoastable, DCSync rights,
   shortest path to Domain Admins, abusable ACLs). Record each attack path / abusable ACL (with the
   query used) in `findings.md`.
5. **Marker + re-collect loop.** Always write a run marker, then re-collect as each new identity is
   gained — paths change:
   ```bash
   if [ -n "$(ls -A "$RUN/collection" 2>/dev/null)" ]; then
     echo "bloodhound: collection imported; paths in findings.md" > "$RUN/summary.txt"
   else
     echo "no collection produced" > "$RUN/summary.txt"
   fi
   grep -qiE '^\- ' "$RUN/findings.md" || echo "- none: no attack path identified this collection" >> "$RUN/findings.md"
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
BloodHound **CE** (Community Edition) is current — match the collector to the CE ingest version.
Collectors: `bloodhound-python` (remote, no host access), `SharpHound` (on a domain host), or
`nxc ldap --bloodhound`. Cypher is the analysis language; keep a query library in RAG.

## Output formats
JSON/zip collection (saved in `$RUN/collection/`); graph UI in BloodHound CE; Cypher query exports.
This skill also writes `$RUN/findings.md` (attack paths + the Cypher used), `$RUN/summary.txt`
(run marker), `$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "bloodhound",
  "target": "<domain>",
  "run_dir": "out/bloodhound/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":  { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "collected":        { "attempted": true, "ok": true, "evidence": "collection" },
    "paths-analyzed":   { "attempted": true, "ok": true, "evidence": "findings.md" },
    "results-recorded": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (collector missing, DC unreachable, bad
creds, out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
**Very high RAG value:** a Cypher-query library ("find kerberoastable", "DCSync rights", "shortest
path to DA"). Consumes creds from `netexec`; feeds `impacket` / `certipy` / `rubeus` attacks and
`hashcat` (kerberoastable/AS-REP hashes). Re-run after every new identity is obtained.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target domain confirmed in scope AND collection scoped to the lab before collecting
    verify: judge
    evidence: notes/scope.txt
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
    evidence: summary.txt
    on_fail: redo-skill
    required: true
```

## Notes / pitfalls
- **Collection is noisy** — scope it to the lab; `scope-confirmed` fails hard (`on_fail: fail`).
- **Match the collector version to the BloodHound CE ingest version**, or import fails / misparses.
- **Re-collect as each new identity is gained** — attack paths change with new group membership.
- Keep Cypher queries in RAG, not hardcoded here, so the library stays current.
- A run that finds no path must still write `summary.txt` and a `- none` line in `findings.md` so
  "ran but empty" ≠ "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/bloodhound/<timestamp>/` (git-ignored).
