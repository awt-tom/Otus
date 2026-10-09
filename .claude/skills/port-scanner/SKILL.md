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
context: fork
agent: recon-runner
background: false
category: recon
domain: network
---

# nmap — port & service scanning

Shared contract: see AGENTS.md.

## Goal
Find useful exposed services quickly, with a truthful inventory of the selected TCP ports and
omissions. A completed common-port profile is not an all-port negative.

## Steps
1. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill port-scanner --target "$target" --profile top-100 --coverage-set 'Selected 100 TCP ports')"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$target" --run-dir "$RUN"`; nonzero STOP. Write notes/task.md with the hypothesis, actual selected set, total allocation and escalation trigger; create scans/.
2. Validate installed Nmap/help locally: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- nmap --version`. Initial scan: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" --timeout 120 --grace 5 -- nmap -sT --top-ports 100 --stats-every 15s -oA "$RUN/scans/initial" "$target"`. Use supplied ports with `-p "$ports"` and a matching profile instead; `-Pn` only for established host-discovery filtering.
3. Derive inventory from native XML, never greppable-output regex:
  `python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- python3 -c 'import json,sys,xml.etree.ElementTree as xml; scan=xml.parse(sys.argv[1]).getroot(); print(json.dumps([{"port":int(port.get("portid")),"protocol":port.get("protocol"),"service":port.find("service").attrib if port.find("service") is not None else {}} for port in scan.findall("./host/ports/port") if port.find("state").get("state")=="open"]))' "$RUN/scans/initial.xml" > "$RUN/evidence/inventory.json"`.
4. Derive `ports="$(python3 -I scripts/otus-log.py run --run-dir "$RUN" --timeout 10 -- python3 -c 'import json,sys; print(",".join(str(item["port"]) for item in json.load(open(sys.argv[1])) if item["protocol"]=="tcp"))' "$RUN/evidence/inventory.json")"`. Only if nonempty and allocation permits: `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$target" --timeout 120 -- nmap -sT -sV --version-light -p "$ports" -oA "$RUN/scans/detail" "$target"`. Record services and native scaninfo/host/runstats in notes/assessment.md. No open ports, down/skipped hosts and filtered ports differ; never invent detail or modify native files.
5. Propose remaining top-1000 ports in 180-second chunks only when cheaper service branches stall; remaining TCP in 300-second chunks only with an explicit lead/deeper objective and remaining allocation. Record exact `-p` sets, deduplicate prior coverage. No default full sweep, minimum rate, broad NSE, aggressive timing or UDP; selected verified NSE needs a separate bounded hypothesis and `--script-timeout`.
6. Set STATUS/STOP from actual coverage: declared set finished -> complete/completed; native early/inconclusive -> partial; helper failure -> error, no further active steps. Only set `--observed` from native port accounting; down/unreported coverage stays unknown. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted 'Unselected TCP ports and UDP' --item 'scope-confirmed=ok:../../scope.json' --item 'declared-profile-scan=ok:scans/initial.xml' --item 'inventory-derived=ok:evidence/inventory.json' --item 'coverage-assessed=ok:notes/assessment.md' --target-state unchanged --cleanup not-needed`; claim ok only where supported. Return service leads to the coordinator.

## Modern tooling & alternatives
Nmap is the baseline; faster scanners are conditional alternatives, not compulsory extra passes.
`-oA` preserves normal/greppable/XML; structured XML is authoritative for the inventory.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Inherited task scope and scan target checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: declared-profile-scan
    desc: Events and native XML substantiate the selected profile and actual outcome
    verify: judge
    evidence: scans/initial.xml
    on_fail: redo-part
    required: true
  - id: inventory-derived
    desc: Clean inventory matches native open-port states; empty list is valid
    verify: judge
    evidence: evidence/inventory.json
    on_fail: redo-part
    required: true
  - id: coverage-assessed
    desc: Actual set, filtering, skipped work, budget and conditional detail accurately assessed
    verify: judge
    evidence: notes/assessment.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- `--host-timeout` can discard a host port table; it is not a generic evidence-preserving budget.
- Forced high rates can turn loss into false negatives. Top ports are a prioritization, not a coverage guarantee.
- A helper deadline remains error even if termination flushes XML; preserve it without continuing scans.
