---
name: port-scanner
description: >
  Use when scanning a host for open TCP ports, services, and versions with nmap
  (port scan, service/version detection, NSE scripts). The backbone recon step for
  HTB/OSCP boxes and network-scope enumeration. Not for subdomain discovery
  (use subfinder) or HTTP fingerprinting (use httpx).
arguments: "target [ports]"
model: inherit
effort: medium
context: inline
agent:
---

# nmap — port & service scanning

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if target not confirmed in scope.

## Goal (desired outcome)
Enumerate open ports, services, and versions on a host and hand a clean, machine-readable
service inventory to downstream per-service skills. This is the backbone of every HTB box
and network-scope recon pass.

## Steps
1. **Precondition / scope.** Confirm `target` is in scope. Record the confirmation so it is
   verifiable, then anchor a timestamped run directory to the repo root (never write under
   `skills/`):
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   RUN="$ROOT/out/port-scanner/$(date +%Y%m%dT%H%M%S)"
   mkdir -p "$RUN/scans" "$RUN/notes"
   echo "target=$target confirmed in scope: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"
   ```
2. **Quick full-port sweep.** Find every open TCP port fast, saving all three formats at once:
   ```bash
   nmap -p- --min-rate 2000 -Pn -oA "$RUN/scans/allports" "$target" | tee -a "$RUN/run.log"
   ```
   (`-Pn` skips host discovery when ICMP is filtered; drop it if host discovery is wanted.)
3. **Extract open ports** from the greppable output:
   ```bash
   ports="$(grep -oE '[0-9]+/open' "$RUN/scans/allports.gnmap" | cut -d/ -f1 | paste -sd, -)"
   echo "open ports: ${ports:-none}" | tee -a "$RUN/run.log"
   ```
   If `ports` is empty, write a "no open ports" marker to **both** the detail scan file and the
   handoff summary, then stop — so "ran but empty" stays distinguishable from "didn't run":
   ```bash
   if [ -z "$ports" ]; then
     echo "no open ports" > "$RUN/scans/detail.nmap"
     echo "no open ports" > "$RUN/summary.txt"
     exit 0
   fi
   ```
4. **Targeted service/version + default scripts** against only the open ports:
   ```bash
   nmap -sCV -p"$ports" -Pn -oA "$RUN/scans/detail" "$target" | tee -a "$RUN/run.log"
   ```
   (`-sCV` = `-sC` default NSE scripts + `-sV` version detection.)
5. **Relevant NSE per service (optional, non-intrusive).** Run targeted scripts only for the
   services found, e.g. SMB enumeration, avoiding intrusive categories unless authorized:
   ```bash
   nmap -sV --script=smb-os-discovery -p"$ports" -Pn -oA "$RUN/scans/nse" "$target" | tee -a "$RUN/run.log"
   ```
6. **Hand-off / branch.** Summarize open services for downstream skills and write the run record:
   ```bash
   { echo "# $target"; grep -E '^[0-9]+/(tcp|udp)[[:space:]]+open' "$RUN/scans/detail.nmap" 2>/dev/null || echo "no open ports"; } > "$RUN/summary.txt"
   ```
   Then branch by service to per-service skills (SMB → enum4linux-ng/smbmap, HTTP(S) → httpx
   / ffuf / web skills), and feed `detail.xml` to exploit lookup (`searchsploit --nmap`).
7. **Write the run record** `_run.json` into `$RUN/` (schema in Output formats) capturing intent,
   per-item status, exit codes, and any hard errors.

## Modern tooling & alternatives
`nmap` remains the standard. For a faster initial port discovery, `rustscan` / `masscan` /
`naabu` can sweep ports, then hand the discovered ports to nmap for `-sCV` service detection.
Use NSE (`--script`) for scripted per-service checks.

## Output formats
`-oA <basename>` emits all three formats at once: normal (`.nmap`), greppable (`.gnmap`), and
XML (`.xml`). The XML feeds `searchsploit --nmap` and reporting; the greppable file is easiest
to parse for open ports. All scans save under `$RUN/scans/`. The executor also writes a run
record `$RUN/_run.json`:
```json
{
  "skill": "port-scanner",
  "target": "<target>",
  "run_dir": "out/port-scanner/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed": { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "allports-scan":   { "attempted": true, "ok": true, "evidence": "scans/allports.nmap", "exit": 0 },
    "service-detail":  { "attempted": true, "ok": true, "evidence": "scans/detail.nmap",   "exit": 0 },
    "handoff-written": { "attempted": true, "ok": true, "evidence": "summary.txt" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (nmap missing, network blocked,
out of scope) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Consumes a confirmed in-scope `target` (often an IP/host from subfinder/httpx). The
XML output feeds exploit-lookup (`searchsploit --nmap`); service results branch to
`enum4linux-ng`, `smbmap`, and the web skills (httpx → ffuf → nuclei).
A GTFOBins/HackTricks RAG note helps map a discovered service → next step. No wordlists needed.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target confirmed in scope before any active scan
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: allports-scan
    desc: Full TCP port sweep completed and saved
    verify: nonempty
    evidence: scans/allports.nmap
    on_fail: redo-part
    required: true
  - id: service-detail
    desc: Version/script scan run against discovered open ports
    verify: contains:(open|no open ports)
    evidence: scans/detail.nmap
    on_fail: redo-part
    required: true
  - id: handoff-written
    desc: Open services summarized for downstream skills
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- `-p-` (all 65535 ports) is slow — pair with `--min-rate` or a fast scanner (rustscan/masscan)
  for the first sweep, then nmap `-sCV` only the open ports.
- Avoid intrusive NSE categories (`exploit`, `brute`, `dos`) unless explicitly authorized; `-sC`
  runs only the `default` category.
- `-Pn` treats the host as online (skips host discovery) — correct when ICMP is filtered, but
  it can hide that a host is actually down.
- A step that legitimately finds nothing (no open ports) must still write a "no open ports"
  marker to both `scans/detail.nmap` and `summary.txt` so "ran but empty" ≠ "didn't run".
- **Save raw evidence to `loot/`** — if a finding (version, status code, response) is used as proof,
  save the raw response to `loot/` (e.g. `curl -s <url> > loot/<name>.html`) so the reviewer can
  hard-verify it.
- Never write scan output under `skills/`; the run directory is always anchored to the repo
  root via `git rev-parse --show-toplevel` under `out/port-scanner/<timestamp>/` (git-ignored).
