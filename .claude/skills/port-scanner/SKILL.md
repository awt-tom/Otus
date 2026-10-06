---
name: port-scanner
description: >
  Use when scanning a host for open TCP ports, services, and versions with nmap
  (port scan, service/version detection, NSE scripts). The backbone recon step for
  HTB/OSCP boxes and network-scope enumeration. Not for subdomain discovery
  (use subfinder) or HTTP fingerprinting (use httpx).
arguments: "target [ports]"
model: inherit
effort: low
context: inline
agent:
category: recon
domain: network
---

# nmap — port & service scanning

Shared contract: see AGENTS.md.

## Goal
Enumerate open ports, services, and versions on a host and hand a clean, machine-readable service
inventory to downstream per-service skills.

## Steps
1. Set up the run dir per AGENTS.md (`$RUN`), `mkdir -p "$RUN/scans"`; scope is inherited from `out/<engagement>/scope.txt`.
2. Full-port sweep (all three formats; `-Pn` when ICMP is filtered): `nmap -p- --min-rate 2000 -Pn -oA "$RUN/scans/allports" "$target" | tee -a "$RUN/run.log"`.
3. Extract open ports: `ports="$(grep -oE '[0-9]+/open' "$RUN/scans/allports.gnmap" | cut -d/ -f1 | paste -sd, -)"`. If none, write `no open ports` to both `scans/detail.nmap` and `findings.md` and stop (empty ≠ didn't-run).
4. Service/version + default scripts on open ports only: `nmap -sCV -p"$ports" -Pn -oA "$RUN/scans/detail" "$target" | tee -a "$RUN/run.log"`. Add non-intrusive NSE per service (e.g. `--script=smb-os-discovery`) as needed.
5. Summarize open services to `findings.md`, feed `detail.xml` to `searchsploit --nmap`, branch by service (SMB→netexec, HTTP→httpx/ffuf), write `run.json`.

## Modern tooling & alternatives
`nmap` stays standard; `rustscan` / `masscan` / `naabu` sweep ports fast, then hand them to nmap for
`-sCV`. NSE (`--script`) runs scripted per-service checks; `-oA` emits normal/greppable/XML at once.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
    on_fail: fail
    required: true
  - id: allports-scan
    desc: Full TCP port sweep completed and saved
    verify: nonempty
    evidence: scans/allports.nmap
    on_fail: redo-part
    required: true
  - id: service-detail
    desc: Version/script scan run against discovered open ports (or "no open ports" marker)
    verify: nonempty
    evidence: scans/detail.nmap
    on_fail: redo-part
    required: true
```

## Notes / pitfalls
- `-p-` (all 65535 ports) is slow — pair with `--min-rate` or a fast scanner first, then nmap `-sCV` only the open ports.
- Avoid intrusive NSE categories (`exploit`, `brute`, `dos`) unless explicitly authorized; `-sC` runs only the `default` category.
- `-Pn` skips host discovery (treats host as up) — correct when ICMP is filtered, but can mask a host that is actually down.
- A run that finds nothing must still write the `no open ports` marker to `scans/detail.nmap` and `findings.md`.
