# Otus

Otus is a library of **offensive-security skills** for an LLM agent. Each skill is a
self-contained runbook (`.claude/skills/<tool>/SKILL.md`) that the agent loads on demand to run a
specific bug-bounty / CTF / lab task — recon, scanning, a web-vuln class, exploitation,
password cracking, privesc, or CTF reversing/forensics — with a consistent structure,
evidence trail, and completion check.

*Otus* (For the love of owls)

> ⚠️ **Authorized use only.** These skills drive real offensive tools. Use them only against
> targets you are explicitly permitted to test: in-scope bug-bounty programs, CTF/HTB labs, or
> systems you own. Scope is confirmed **once per engagement** (recorded in `out/<engagement>/scope.txt`)
> and inherited by every run; work stops if the target isn't confirmed in scope.

## How a skill works

Each `SKILL.md` is deliberately slim and tool-specific (see `templates/SKILL.template.md`):

- **YAML frontmatter** — `name` (equals the folder), `description`, `arguments`, `model`, `effort`,
  `context`, `agent`, `category`, and `domain`.
- **Shared contract** — one line, `Shared contract: see AGENTS.md`, instead of re-stating the
  scope gate, run-dir layout, guardrail rule, etc. in every body.
- **Tool-specific body** — Goal, Steps (the real commands), Modern tooling, a `## Checklist` of
  the tool-unique verifiable items, and tool-specific pitfalls.
- **Checklist** — a fenced `yaml` block of verifiable items (`verify: exists | nonempty |
  contains:<regex> | min-lines:<n> | exit-zero | judge`). The scope-confirmed item is always
  `on_fail: fail` and references the inherited `out/<engagement>/scope.txt`. Any step that can
  legitimately produce nothing still writes a marker file, so "ran but empty" ≠ "didn't run".
- **Run record** — every run writes its evidence, `run.log`, a human-readable `findings.md`, and a
  `run.json` into `out/<engagement>/<tool>/<timestamp>/` (anchored at the repo root). Output is never
  written under `.claude/skills/`. `out/` is git-ignored.

The behavioural rules every skill shares — authorization, evidence layout, the `run.json` schema,
guardrail handling, non-interactive execution, cleanup verification — live **once** in
[`AGENTS.md`](AGENTS.md).

## How to use it

Otus doesn't replace the tools — it drives them. You still need the underlying binaries
(nmap, subfinder, httpx, ffuf, nuclei, sqlmap, etc.) installed, e.g. on Kali or via each
tool's install docs.

1. **Point your agent at a skill.** In an agent session with this repo as context, ask for the
   capability — e.g. *"run the `port-scanner` skill against 10.10.10.5"*. The agent loads
   `.claude/skills/port-scanner/SKILL.md` and follows it.
2. **Confirm scope once.** At the start of an engagement, confirm the target is authorized and
   record it in `out/<engagement>/scope.txt`. Every skill inherits that single confirmation.
3. **Pass arguments.** Each skill's frontmatter declares its `arguments` (e.g. `port-scanner` takes
   `target [ports]`, `subfinder` takes a domain).
4. **Collect evidence.** Results, a `run.log`, a `findings.md`, and a `run.json` land in
   `out/<engagement>/<tool>/<timestamp>/` (git-ignored).
5. **Verify the run.** Hand the run directory to the `reviewer` (skill or subagent) to check it
   against the skill's `## Checklist` and return a PASS / FAILED verdict.

## Runtimes

Otus is portable across agent runtimes. [`AGENTS.md`](AGENTS.md) is the single, runtime-agnostic
contract; the runtime-specific instruction files are **generated** from it.

- **Claude Code & OpenCode** read `.claude/skills/` natively — skills are flat, one tool-named
  folder per skill (`.claude/skills/<tool>/SKILL.md`). Claude Code also uses the subagents in
  `.claude/agents/` and the routing appendix in `CLAUDE.md`.
- **GitHub Copilot** — point its config `skillDirectories` at `./.claude/skills` so it can load the
  skills (verify the exact key name in your setup). `.github/copilot-instructions.md` is
  auto-included per session.
- **Regenerate the adapters** after editing the contract:
  ```bash
  python3 -I scripts/build-runtimes.py   # regenerates CLAUDE.md + .github/copilot-instructions.md
  ```
  Edit `AGENTS.md`, never the generated `CLAUDE.md` / `.github/copilot-instructions.md`.

## Skill catalog

The full, generated browse-index — every skill by **function** and by **domain** — is
[`docs/catalog.md`](docs/catalog.md) (regenerate with `python3 -I scripts/build-catalog.py`).

| Category | Skills |
|---|---|
| **Recon** | `subfinder` · `httpx` · `port-scanner` · `ffuf` |
| **Web** | `nuclei` · `sqlmap` · `xss` · `ssrf` · `idor` · `burpsuite` |
| **Access** | `exploitation` · `metasploit` · `hydra` · `ssh-foothold` |
| **AD / network** | `netexec` · `bloodhound` · `impacket` |
| **Privesc / creds** | `linpeas` · `privesc-root` · `hashcat` |
| **RE / forensics** | `ghidra` · `pwntools` · `binwalk` · `steghide` · `wireshark` |
| **Meta** | `review` |

## Claude Code agent layer

`CLAUDE.md` (generated) defines runtime routing, and `.claude/agents/` holds four subagents
that run skills in isolated contexts:

- **`recon-runner`** — runs read-heavy recon/enumeration (subfinder, httpx, port-scanner, ffuf)
  and returns a concise summary instead of raw dumps.
- **`vuln-hunter`** — runs the scan → triage → (lab-only) exploit loop for nuclei and the
  web-vuln / exploitation skills.
- **`reviewer`** — read-only; independently verifies a run against its `## Checklist` on disk and
  returns a verdict (PASS / FAILED-RECOVERED / FAILED / NON-COMPLIANT).
- **`reporter`** — read-only over `out/`; compiles the reviewed evidence into the final engagement
  report (canonical markdown plus a branded, self-contained HTML, print-ready via Save-as-PDF).
  Writes only under `out/<engagement>/report/`.

## Repository layout

```
AGENTS.md                        # the canonical, runtime-agnostic agent contract (edit this)
CLAUDE.md                        # GENERATED from AGENTS.md + Claude Code routing appendix
.github/copilot-instructions.md  # GENERATED from AGENTS.md + a Copilot note
.claude/skills/<tool>/SKILL.md   # one capability per tool-named folder; the runbook the agent loads
.claude/agents/                  # recon-runner, vuln-hunter, reviewer, reporter subagents
docs/authoring.md                # skill-authoring + verification spec, tool catalog, conventions
docs/catalog.md                  # GENERATED human browse-index (by function + by domain)
templates/                       # SKILL.template.md, report.css
scripts/                         # build-runtimes.py, build-catalog.py
out/                             # timestamped run evidence, grouped by engagement (git-ignored)
```

## Docs

- [`AGENTS.md`](AGENTS.md) — the shared agent contract (authorization, evidence layout, `run.json`,
  guardrail handling, non-interactive execution, cleanup, self-report).
- [`docs/authoring.md`](docs/authoring.md) — skill format, metadata schema, the `## Checklist`
  verification spec, the tool catalog, the model/effort convention, and the build order.
- [`docs/catalog.md`](docs/catalog.md) — the generated browse-index of every skill.

## Maintainer

Otus is built and maintained by **Tom** ([@awt-tom](https://github.com/awt-tom)) of
[Security with Tom](https://securitywithtom.com) — home of Otus.
