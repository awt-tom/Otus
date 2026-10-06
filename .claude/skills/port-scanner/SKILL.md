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
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill port-scanner --target "$target")"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$target" --run-dir "$RUN"`; nonzero STOP. `mkdir -p "$RUN/scans"`.
2. Full sweep: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" -- nmap -p- --min-rate 2000 -Pn -oA "$RUN/scans/allports" "$target"` (timeouts per AGENTS.md).
3. Extract ports: `ports="$(grep -oE '[0-9]+/open' "$RUN/scans/allports.gnmap" | cut -d/ -f1 | paste -sd, -)"`. If none, write `no open ports` to `scans/detail.nmap`, skip step 4, and finish with that summary (empty is not failure).
4. Detail: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" -- nmap -sCV -p"$ports" -Pn -oA "$RUN/scans/detail" "$target"`. Add non-intrusive NSE per service (e.g. `--script=smb-os-discovery`) as needed.
5. Save service notes, wrap `searchsploit --nmap` with the helper if used, and branch SMB to netexec / HTTP to httpx/ffuf. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status complete --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'allports-scan=ok:scans/allports.nmap' --item 'service-detail=ok:scans/detail.nmap' --target-state unchanged --cleanup not-needed`.

## Modern tooling & alternatives
`nmap` stays standard; `rustscan` / `masscan` / `naabu` sweep ports fast, then hand them to nmap for
`-sCV`. NSE (`--script`) runs scripted per-service checks; `-oA` emits normal/greppable/XML at once.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization and scan target checked
    verify: judge
    evidence: ../../scope.json
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
- A run with no ports writes the marker to `scans/detail.nmap`; finish renders the matching summary.
