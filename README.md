# Otus

Otus is a library of **offensive-security skills** for an LLM agent. Each skill is a
self-contained runbook (`.claude/skills/<name>/SKILL.md`) that the agent loads on demand to run a
specific bug-bounty / CTF / lab task — recon, scanning, a web-vuln class, exploitation,
password cracking, privesc, or CTF reversing/forensics — with a consistent structure,
evidence trail, and completion check.

*Otus* (For the love of owls)

> ⚠️ **Authorized use only.** These skills drive real offensive tools. Use them only against
> targets you are explicitly permitted to test: in-scope bug-bounty programs, CTF/HTB labs, or
> systems you own. Every skill begins with a scope-guard line and aborts if the target isn't
> confirmed in scope.

## How a skill works

Each `SKILL.md` follows a fixed template (see `docs/skill-generator-guide.md`):

- **YAML frontmatter** — `name` (equals the folder), `description`, `arguments`, and
  model/effort/context/agent hints.
- **Scope guard** — first line of the body; authorized targets only.
- **Body sections, in order** — Goal, Steps, Modern tooling & alternatives, Output formats,
  RAG / shared data / cross-skill, **Checklist**, Notes / pitfalls.
- **Checklist** — a fenced `yaml` block of verifiable items (`verify: exists | nonempty |
  contains:<regex> | min-lines:<n> | exit-zero | judge`). The scope gate is always
  `on_fail: fail`. Any step that can legitimately produce nothing still writes a marker file,
  so "ran but empty" ≠ "didn't run".
- **Run record** — every run writes its evidence, a `run.log`, a human-readable `findings.md`, and a
  `run.json` to a timestamped `out/<engagement>/<name>/<timestamp>/` folder anchored at the repo root
  (`git rev-parse --show-toplevel`). Output is never written under `.claude/skills/`. `out/` is
  git-ignored.

## How to use it

Otus doesn't replace the tools — it drives them. You still need the underlying binaries
(nmap, subfinder, httpx, ffuf, nuclei, sqlmap, etc.) installed, e.g. on Kali or via each
tool's install docs.

1. **Point your agent at a skill.** In an agent session (Claude Code, Copilot, or similar)
   with this repo as context, ask for the capability — for example *"run the `port-scanner`
   skill against 10.10.10.5"*. The agent loads `.claude/skills/port-scanner/SKILL.md` and follows it.
2. **Pass arguments.** Each skill's frontmatter declares its `arguments` (e.g.
   `port-scanner` takes `target [ports]`, `subfinder` takes a domain). Provide the target and
   any options the skill asks for.
3. **Confirm scope.** The skill's scope guard requires an authorized target. Only run against
   in-scope programs, CTF/HTB labs, or systems you own — the skill aborts otherwise.
4. **Collect evidence.** Results, a `run.log`, a `findings.md`, and a `run.json` land in
   `out/<engagement>/<name>/<timestamp>/` at the repo root (git-ignored). Nothing is written under `.claude/skills/`.
5. **Verify the run.** Hand the run directory to the `reviewer` (skill or subagent) to check it
   against the skill's `## Checklist` and return a PASS / FAILED verdict.

**Typical chain:** `subfinder` (subdomains) → `httpx` (live hosts) → `port-scanner` + `ffuf`
(ports & content) → `nuclei` (scan) → web-vuln class skills (`sqlmap`, `xss`, `ssrf`, `idor`) →
`exploitation` → `privesc-root` (AD / password skills as needed), with `review` after each stage
and the `reporter` compiling the final report at the end.

With the [Claude Code agent layer](#claude-code-agent-layer), delegate recon to `recon-runner`,
scanning/exploitation to `vuln-hunter`, verification to `reviewer`, and the final report to
`reporter`; `CLAUDE.md` routes tasks automatically.

## Skill catalog

| Category | Skills |
|---|---|
| **Recon & enumeration** | `subfinder` (passive subdomains) · `httpx` (HTTP probe/fingerprint) · `port-scanner` (nmap port/service scan) · `ffuf` (content/endpoint fuzzing) |
| **Vulnerability scanning** | `nuclei` (template-based scanner) |
| **Web-vuln classes** | `sqlmap` (SQLi) · `xss` · `ssrf` · `idor` (IDOR/BOLA) · `burpsuite` (manual web-testing methodology) |
| **Exploitation** | `metasploit` (framework) · `exploitation` (manual/scripted non-msfconsole PoCs) · `ssh-foothold` (validate a supplied SSH credential, land an initial foothold) · `pwntools` (exploit dev) |
| **Active Directory / network** | `netexec` (AD swiss-army knife) · `bloodhound` (attack-path analysis) · `impacket` (protocol tools) |
| **Passwords & credentials** | `hashcat` (GPU hash cracking) · `hydra` (online login brute-force) |
| **Privilege escalation** | `linpeas` / winpeas (privesc enumeration) · `privesc-root` (escalate a foothold to root, prove uid=0, capture the flag) |
| **CTF: reversing & forensics** | `ghidra` (decompiler) · `wireshark` / tshark (packet analysis) · `binwalk` (firmware/file carving) · `steghide` (steganography) |
| **Meta** | `review` (independent completion check & remediation) |

## Claude Code agent layer

`CLAUDE.md` (repo root) defines runtime routing, and `.claude/agents/` holds four subagents
that run skills in isolated contexts:

- **`recon-runner`** — runs read-heavy recon/enumeration (subfinder, httpx, port-scanner, ffuf)
  and returns a concise summary instead of raw dumps.
- **`vuln-hunter`** — runs the scan → triage → (lab-only) exploit loop for nuclei and the
  web-vuln / exploitation skills.
- **`reviewer`** — read-only, independently verifies a run against its `## Checklist` on disk and
  returns a verdict (PASS / FAILED-RECOVERED / FAILED / NON-COMPLIANT). It never runs
  target-facing tools.
- **`reporter`** — read-only over `out/`; compiles the reviewed evidence into the final
  engagement report — canonical markdown plus a branded, self-contained HTML (print-ready,
  Save-as-PDF from any browser; no rendering dependency). Writes only under `out/<engagement>/report/` and
  never contacts targets.

Recon-oriented and scanning/exploitation skills carry a routing line pointing at the matching
subagent, every run is handed to the `reviewer` before results are treated as final, and at the
end of an engagement the `reporter` turns the reviewed runs into the deliverable report.

## Repository layout

```
.claude/skills/<name>/SKILL.md   # one capability per folder; the runbook the agent loads
.claude/agents/          # recon-runner, vuln-hunter, reviewer, reporter subagents
CLAUDE.md                # runtime routing rules + hard safety invariants
docs/                    # authoring + verification specs
out/                     # timestamped run evidence, grouped by engagement (git-ignored)
```

## Docs

- `docs/skill-generator-guide.md` — skill format, metadata schema, body template,
  model/effort/context guidance, tool catalog, repo layout, and build order.
- `docs/skill-review-guide.md` — the `## Checklist` spec, the `run.json` run record,
  and the Reviewer skill.

## Maintainer

Otus is built and maintained by **Tom** ([@awt-tom](https://github.com/awt-tom)) of
[Security with Tom](https://securitywithtom.com) — home of Otus.
