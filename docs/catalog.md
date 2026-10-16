<!-- GENERATED from .claude/skills/*/SKILL.md frontmatter — do not edit directly.
     Regenerate with: python3 -I scripts/build-catalog.py -->

# Otus skill catalog

27 skills, each a flat runbook at `.claude/skills/<tool>/SKILL.md`. This index is generated from skill frontmatter — see `docs/authoring.md` to add one.

## By function

Grouped by `category`; each row is **name** — description — _(domain)_.

### recon

- **ffuf** — Use when fuzzing a web target for hidden directories, files, parameters, or virtual hosts — content discovery / directory brute-forcing with ffuf. Wordlist-driven; its hits feed LFI/upload/IDOR and manual/Burp testing. Not for subdomain discovery (use subfinder) or template-based vuln scanning (use nuclei). _(web)_
- **httpx** — Use when probing a host/subdomain list to find which are live over HTTP(S) and fingerprint them — status code, title, tech, IP, CDN — with httpx (ProjectDiscovery, not the Python httpx library). The "what's actually reachable" filter between subfinder/dnsx and katana/nuclei. Not for port scanning (use port-scanner) or subdomain discovery (use subfinder). _(web)_
- **port-scanner** — Use when scanning a host for open TCP ports, services, and versions with nmap (port scan, service/version detection, NSE scripts). The backbone recon step for HTB/OSCP boxes and network-scope enumeration. Not for subdomain discovery (use subfinder) or HTTP fingerprinting (use httpx). _(network)_
- **subfinder** — Use when enumerating subdomains of an in-scope apex domain — passive subdomain discovery and attack-surface mapping with subfinder (ProjectDiscovery). The first recon stage; its subdomain list feeds dnsx → httpx → nuclei/katana. Not for port scanning (use port-scanner) or active DNS brute-forcing. _(network)_

### web

- **burpsuite** — Use when manually testing a web application with Burp Suite — intercepting proxy, mapping the app, Repeater-driven exploitation, Intruder fuzzing, and authz/logic testing. A GUI methodology (set scope → proxy/map → Repeater → Intruder → export), the manual hub that feeds sqlmap and the vuln-category skills. Not for automated template scanning (use nuclei) or pure content discovery (use ffuf). _(web)_
- **idor** — Use when testing for broken object/access control — IDOR / BOLA — on an authorized web target: endpoints that reference objects by ID (numeric, UUID, filename) where swapping the reference grants horizontal or vertical access. A methodology (enumerate IDs → swap/escalate → authz matrix). Also known as broken access control. Not for XSS/SSRF. _(web)_
- **nuclei** — Use when scanning live web hosts for known CVEs, misconfigurations, exposures, and subdomain takeovers with nuclei (template-based vulnerability scanner). Consumes the httpx live-host list; triage of every hit is mandatory before reporting. Not for content discovery (use ffuf) or port scanning (use port-scanner). _(web)_
- **sqlmap** — Use when confirming and exploiting SQL injection (SQLi) on an authorized target with sqlmap — DBMS fingerprint, data extraction (--dump), file read, OS shell. Input is a captured request (-r req.txt), often from ffuf/Burp-found parameters. Not for generic content discovery (use ffuf) or template-based scanning (use nuclei). _(web)_
- **ssrf** — Use when testing for server-side request forgery (SSRF) on an authorized web target — parameters that make the server fetch a URL, cloud metadata (169.254.169.254), internal services, filter bypasses. A testing methodology (param ID → internal targets → bypass → impact) using an OOB collaborator and RAG payloads. Not for client-side XSS (use xss). _(web)_
- **xss** — Use when testing for cross-site scripting — reflected, stored, or DOM XSS — on an authorized web target. A testing methodology (context analysis → payload per sink → confirm → impact PoC) that invokes dalfox and Burp and pulls payloads from RAG. Not for SQL injection (use sqlmap) or content discovery (use ffuf). _(web)_

### access

- **exploitation** — Use when running a manual or scripted exploit proof-of-concept (NON-Metasploit) against a confirmed, authorized target — a hand-written / searchsploit / ExploitDB / GitHub PoC that establishes remote code execution or concrete impact, with the request/response or shell transcript captured as proof. Input is service/version detail from nmap. Not for msfconsole modules (use metasploit), template scanning (nuclei), or privilege escalation to root (privesc-root). _(host)_
- **hydra** — Use when brute-forcing or password-spraying an online login service with hydra — ssh, ftp, rdp, smb, and HTTP login forms (http-post-form / http-get-form) — using a user/password list to find valid credentials. Consumes wordlists; feeds valid creds to login/AD/web skills. Not for offline hash cracking (use hashcat) and not for web content discovery (use ffuf). _(network)_
- **metasploit** — Use when exploiting a confirmed, authorized target with the Metasploit Framework (msfconsole) — select/configure an exploit or auxiliary module, run `check`, deliver a payload, and manage sessions / post-exploitation. Input is service/version detail from nmap. Not for content discovery (ffuf) or template scanning (nuclei); prefer single searchsploit/GitHub exploits for OSCP-style manual work. _(host)_
- **ssh-foothold** — Use when validating a SUPPLIED SSH credential (password or private key) against a confirmed, authorized target and, on success, landing an initial read-only foothold — a one-shot `id`/`hostname` proof, light non-destructive enumeration, and the user flag if present. A single credential test, NOT a brute-force spray (use hydra for online brute, netexec for SMB/WinRM). Runs non-interactively (no expect, no held shell). _(host)_

### ad-network

- **bloodhound** — Use when mapping Active Directory privilege-escalation / lateral-movement paths with BloodHound CE — collect AD objects (bloodhound-python / SharpHound / nxc --bloodhound), import, and run Cypher queries to find the shortest path to high-value targets (e.g. Domain Admin) and abusable ACLs. Consumes creds from netexec; feeds impacket/certipy. Not for credential spraying (netexec) or exploitation (metasploit/impacket). _(ad)_
- **impacket** — Use for AD/Windows protocol actions with the Impacket example scripts once you have creds or hashes (often from netexec) — RCE (psexec/wmiexec), credential dumping (secretsdump, incl. DCSync -just-dc), Kerberoast (GetUserSPNs -request), AS-REP roast (GetNPUsers -request), NTLM relay (ntlmrelayx). Feeds hashes to hashcat. Not for attack-path mapping (bloodhound) or web (burpsuite). _(ad)_
- **netexec** — Use when authenticating to and enumerating Windows/AD services at scale with netexec (nxc, the maintained CrackMapExec fork) — SMB/WinRM/LDAP/MSSQL/RDP: spray creds, enumerate shares/users, RID-brute, run modules (gpp_password, laps, kerberoast), confirm access. Feeds impacket/BloodHound. Not for web testing (burpsuite) or single-host exploits (metasploit). Account-lockout risk — check policy before spraying. _(ad)_

### privesc-creds

- **hashcat** — Use when cracking captured password hashes with hashcat (GPU) to recover plaintext for auth / lateral movement — identify the hash type, map to -m <mode>, run wordlist → rules → mask attacks, and list cracked with --show. Consumes hashes from secretsdump/responder/web dumps (incl. Kerberoast/AS-REP from impacket); feeds netexec/login skills. Not for online login brute (use hydra). _(crypto)_
- **linpeas** — Use after an initial foothold to enumerate local privilege-escalation vectors on a compromised host with linpeas/winpeas (PEASS-ng) — SUID, capabilities, cron, creds, misconfigs, kernel — then turn red/yellow highlights into concrete abuse via GTFOBins/LOLBAS. Runs after a foothold skill; feeds the privesc exploit step. Not for remote/network enum (nmap/netexec). _(host)_
- **privesc-root** — Use when escalating an authorized foothold to root and proving it — run the chosen privesc vector (SUID/sudo/cron/capability/kernel or a known-vulnerable local service), capture a non-destructive uid=0 transcript as proof, and grab /root/root.txt. Consumes a vector from linpeas/searchsploit or a foothold from metasploit/web-exploit. Not for enumeration (linpeas) or framework exploitation (metasploit). _(host)_

### re-forensics

- **binwalk** — Use to detect and extract embedded or hidden files inside a blob (firmware image, picture, odd file) — the classic forensics/stego first move. Signature-scan, extract (-e), and recurse (-Me) into nested content, then hand carved output to RE/stego skills. Not for passphrase stego in images/audio (use steghide) or pcap analysis (use wireshark). _(forensics)_
- **ghidra** — Use to statically reverse-engineer an unknown binary with Ghidra — decompile to C-like pseudocode, map logic, and find the check/flag/vuln — driving analysis via the GUI methodology or the headless analyzeHeadless scripting for automation. Extracted algorithm/constraints feed pwntools (exploit) or a z3/script solve. Not for dynamic exploitation (use pwntools/gdb). _(binary)_
- **pwntools** — Use for binary-exploitation / pwn challenges — script interaction with a local or remote binary and build a working exploit (I/O, packing, offsets, ROP, shellcode, format-string) with the pwntools Python framework. Iterate local-first, then fire remote to capture the flag. Pairs with ghidra/radare2 for the static side. _(binary)_
- **steghide** — Use to extract (or embed) data hidden in images/audio with steghide (passphrase-protected LSB stego) — pull a hidden payload with a known/guessed passphrase, probe with info, or crack the passphrase with stegseek + a wordlist. A forensics/stego companion; recovered payloads feed RE/crypto skills. Not for PNG/BMP LSB without steghide (use zsteg) or firmware carving (binwalk). _(forensics)_
- **wireshark** — Use to analyze a packet capture (pcap) and extract secrets/flags/artifacts — follow streams, carve transferred files, and decode protocols — preferring headless tshark for scriptable extraction inside the skill. Carved payloads feed binwalk/stego/crypto skills. Not for live attack traffic generation; this is analysis of an existing capture. _(forensics)_

### meta

- **hexstrike** — Use when running ONE specific authorized HexStrike AI MCP tool (the hexstrike_mcp.py stdio bridge to the local hexstrike_server.py engine) — nmap_scan, nuclei_scan, ffuf_scan, sqlmap_scan, etc. — and recording it in the Otus evidence trail. Call the exact curated tool, never the ~150-tool catalog. Not for direct-CLI control with full flags (use port-scanner, nuclei, ffuf, sqlmap for that). _(misc)_
- **review** — Use after a terminal skill or report run to independently verify its declared profile, actual evidence, coverage and conditional proof claims. Read-only verification requests permitted local repairs from the coordinator, never replays target actions. Trigger with "review", "verify", "did it finish", or "check the <skill> run". _(misc)_

## By domain

Grouped by `domain`; each row is **name** — description — _(category)_.

### web

- **burpsuite** — Use when manually testing a web application with Burp Suite — intercepting proxy, mapping the app, Repeater-driven exploitation, Intruder fuzzing, and authz/logic testing. A GUI methodology (set scope → proxy/map → Repeater → Intruder → export), the manual hub that feeds sqlmap and the vuln-category skills. Not for automated template scanning (use nuclei) or pure content discovery (use ffuf). _(web)_
- **ffuf** — Use when fuzzing a web target for hidden directories, files, parameters, or virtual hosts — content discovery / directory brute-forcing with ffuf. Wordlist-driven; its hits feed LFI/upload/IDOR and manual/Burp testing. Not for subdomain discovery (use subfinder) or template-based vuln scanning (use nuclei). _(recon)_
- **httpx** — Use when probing a host/subdomain list to find which are live over HTTP(S) and fingerprint them — status code, title, tech, IP, CDN — with httpx (ProjectDiscovery, not the Python httpx library). The "what's actually reachable" filter between subfinder/dnsx and katana/nuclei. Not for port scanning (use port-scanner) or subdomain discovery (use subfinder). _(recon)_
- **idor** — Use when testing for broken object/access control — IDOR / BOLA — on an authorized web target: endpoints that reference objects by ID (numeric, UUID, filename) where swapping the reference grants horizontal or vertical access. A methodology (enumerate IDs → swap/escalate → authz matrix). Also known as broken access control. Not for XSS/SSRF. _(web)_
- **nuclei** — Use when scanning live web hosts for known CVEs, misconfigurations, exposures, and subdomain takeovers with nuclei (template-based vulnerability scanner). Consumes the httpx live-host list; triage of every hit is mandatory before reporting. Not for content discovery (use ffuf) or port scanning (use port-scanner). _(web)_
- **sqlmap** — Use when confirming and exploiting SQL injection (SQLi) on an authorized target with sqlmap — DBMS fingerprint, data extraction (--dump), file read, OS shell. Input is a captured request (-r req.txt), often from ffuf/Burp-found parameters. Not for generic content discovery (use ffuf) or template-based scanning (use nuclei). _(web)_
- **ssrf** — Use when testing for server-side request forgery (SSRF) on an authorized web target — parameters that make the server fetch a URL, cloud metadata (169.254.169.254), internal services, filter bypasses. A testing methodology (param ID → internal targets → bypass → impact) using an OOB collaborator and RAG payloads. Not for client-side XSS (use xss). _(web)_
- **xss** — Use when testing for cross-site scripting — reflected, stored, or DOM XSS — on an authorized web target. A testing methodology (context analysis → payload per sink → confirm → impact PoC) that invokes dalfox and Burp and pulls payloads from RAG. Not for SQL injection (use sqlmap) or content discovery (use ffuf). _(web)_

### ad

- **bloodhound** — Use when mapping Active Directory privilege-escalation / lateral-movement paths with BloodHound CE — collect AD objects (bloodhound-python / SharpHound / nxc --bloodhound), import, and run Cypher queries to find the shortest path to high-value targets (e.g. Domain Admin) and abusable ACLs. Consumes creds from netexec; feeds impacket/certipy. Not for credential spraying (netexec) or exploitation (metasploit/impacket). _(ad-network)_
- **impacket** — Use for AD/Windows protocol actions with the Impacket example scripts once you have creds or hashes (often from netexec) — RCE (psexec/wmiexec), credential dumping (secretsdump, incl. DCSync -just-dc), Kerberoast (GetUserSPNs -request), AS-REP roast (GetNPUsers -request), NTLM relay (ntlmrelayx). Feeds hashes to hashcat. Not for attack-path mapping (bloodhound) or web (burpsuite). _(ad-network)_
- **netexec** — Use when authenticating to and enumerating Windows/AD services at scale with netexec (nxc, the maintained CrackMapExec fork) — SMB/WinRM/LDAP/MSSQL/RDP: spray creds, enumerate shares/users, RID-brute, run modules (gpp_password, laps, kerberoast), confirm access. Feeds impacket/BloodHound. Not for web testing (burpsuite) or single-host exploits (metasploit). Account-lockout risk — check policy before spraying. _(ad-network)_

### network

- **hydra** — Use when brute-forcing or password-spraying an online login service with hydra — ssh, ftp, rdp, smb, and HTTP login forms (http-post-form / http-get-form) — using a user/password list to find valid credentials. Consumes wordlists; feeds valid creds to login/AD/web skills. Not for offline hash cracking (use hashcat) and not for web content discovery (use ffuf). _(access)_
- **port-scanner** — Use when scanning a host for open TCP ports, services, and versions with nmap (port scan, service/version detection, NSE scripts). The backbone recon step for HTB/OSCP boxes and network-scope enumeration. Not for subdomain discovery (use subfinder) or HTTP fingerprinting (use httpx). _(recon)_
- **subfinder** — Use when enumerating subdomains of an in-scope apex domain — passive subdomain discovery and attack-surface mapping with subfinder (ProjectDiscovery). The first recon stage; its subdomain list feeds dnsx → httpx → nuclei/katana. Not for port scanning (use port-scanner) or active DNS brute-forcing. _(recon)_

### host

- **exploitation** — Use when running a manual or scripted exploit proof-of-concept (NON-Metasploit) against a confirmed, authorized target — a hand-written / searchsploit / ExploitDB / GitHub PoC that establishes remote code execution or concrete impact, with the request/response or shell transcript captured as proof. Input is service/version detail from nmap. Not for msfconsole modules (use metasploit), template scanning (nuclei), or privilege escalation to root (privesc-root). _(access)_
- **linpeas** — Use after an initial foothold to enumerate local privilege-escalation vectors on a compromised host with linpeas/winpeas (PEASS-ng) — SUID, capabilities, cron, creds, misconfigs, kernel — then turn red/yellow highlights into concrete abuse via GTFOBins/LOLBAS. Runs after a foothold skill; feeds the privesc exploit step. Not for remote/network enum (nmap/netexec). _(privesc-creds)_
- **metasploit** — Use when exploiting a confirmed, authorized target with the Metasploit Framework (msfconsole) — select/configure an exploit or auxiliary module, run `check`, deliver a payload, and manage sessions / post-exploitation. Input is service/version detail from nmap. Not for content discovery (ffuf) or template scanning (nuclei); prefer single searchsploit/GitHub exploits for OSCP-style manual work. _(access)_
- **privesc-root** — Use when escalating an authorized foothold to root and proving it — run the chosen privesc vector (SUID/sudo/cron/capability/kernel or a known-vulnerable local service), capture a non-destructive uid=0 transcript as proof, and grab /root/root.txt. Consumes a vector from linpeas/searchsploit or a foothold from metasploit/web-exploit. Not for enumeration (linpeas) or framework exploitation (metasploit). _(privesc-creds)_
- **ssh-foothold** — Use when validating a SUPPLIED SSH credential (password or private key) against a confirmed, authorized target and, on success, landing an initial read-only foothold — a one-shot `id`/`hostname` proof, light non-destructive enumeration, and the user flag if present. A single credential test, NOT a brute-force spray (use hydra for online brute, netexec for SMB/WinRM). Runs non-interactively (no expect, no held shell). _(access)_

### crypto

- **hashcat** — Use when cracking captured password hashes with hashcat (GPU) to recover plaintext for auth / lateral movement — identify the hash type, map to -m <mode>, run wordlist → rules → mask attacks, and list cracked with --show. Consumes hashes from secretsdump/responder/web dumps (incl. Kerberoast/AS-REP from impacket); feeds netexec/login skills. Not for online login brute (use hydra). _(privesc-creds)_

### binary

- **ghidra** — Use to statically reverse-engineer an unknown binary with Ghidra — decompile to C-like pseudocode, map logic, and find the check/flag/vuln — driving analysis via the GUI methodology or the headless analyzeHeadless scripting for automation. Extracted algorithm/constraints feed pwntools (exploit) or a z3/script solve. Not for dynamic exploitation (use pwntools/gdb). _(re-forensics)_
- **pwntools** — Use for binary-exploitation / pwn challenges — script interaction with a local or remote binary and build a working exploit (I/O, packing, offsets, ROP, shellcode, format-string) with the pwntools Python framework. Iterate local-first, then fire remote to capture the flag. Pairs with ghidra/radare2 for the static side. _(re-forensics)_

### forensics

- **binwalk** — Use to detect and extract embedded or hidden files inside a blob (firmware image, picture, odd file) — the classic forensics/stego first move. Signature-scan, extract (-e), and recurse (-Me) into nested content, then hand carved output to RE/stego skills. Not for passphrase stego in images/audio (use steghide) or pcap analysis (use wireshark). _(re-forensics)_
- **steghide** — Use to extract (or embed) data hidden in images/audio with steghide (passphrase-protected LSB stego) — pull a hidden payload with a known/guessed passphrase, probe with info, or crack the passphrase with stegseek + a wordlist. A forensics/stego companion; recovered payloads feed RE/crypto skills. Not for PNG/BMP LSB without steghide (use zsteg) or firmware carving (binwalk). _(re-forensics)_
- **wireshark** — Use to analyze a packet capture (pcap) and extract secrets/flags/artifacts — follow streams, carve transferred files, and decode protocols — preferring headless tshark for scriptable extraction inside the skill. Carved payloads feed binwalk/stego/crypto skills. Not for live attack traffic generation; this is analysis of an existing capture. _(re-forensics)_

### misc

- **hexstrike** — Use when running ONE specific authorized HexStrike AI MCP tool (the hexstrike_mcp.py stdio bridge to the local hexstrike_server.py engine) — nmap_scan, nuclei_scan, ffuf_scan, sqlmap_scan, etc. — and recording it in the Otus evidence trail. Call the exact curated tool, never the ~150-tool catalog. Not for direct-CLI control with full flags (use port-scanner, nuclei, ffuf, sqlmap for that). _(meta)_
- **review** — Use after a terminal skill or report run to independently verify its declared profile, actual evidence, coverage and conditional proof claims. Read-only verification requests permitted local repairs from the coordinator, never replays target actions. Trigger with "review", "verify", "did it finish", or "check the <skill> run". _(meta)_
