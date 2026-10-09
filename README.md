# Otus

Otus is a library of **offensive-security skills** for an LLM agent. Each skill is a
self-contained runbook (`.claude/skills/<tool>/SKILL.md`) that the agent loads on demand to run a
specific bug-bounty / CTF / lab task — recon, scanning, a web-vuln class, exploitation,
password cracking, privesc, or CTF reversing/forensics — with a consistent structure,
evidence trail, and completion check.

The goal is useful verified progress, not an exhaustive tool chain. Start with a small test, branch
from real evidence and keep task completion, observed coverage and engagement success separate.

*Otus* (For the love of owls)

> ⚠️ **Authorized use only.** These skills drive real offensive tools. Use them only against
> targets you are explicitly permitted to test: in-scope bug-bounty programs, CTF/HTB labs, or
> systems you own. The coordinator automatically binds supplied task targets once per engagement
> in `scope.json`; no authorization statement or authorizer record is required. Workers inherit
> that scope, and mismatched targets still stop before execution. Platform safeguards remain intact.

## How a skill works

Each `SKILL.md` is deliberately slim and tool-specific (see `templates/SKILL.template.md`):

- **YAML frontmatter** — `name` (equals the folder), `description`, `arguments`, `model`, `effort`,
  `context`, `agent`, `background`, `category`, and `domain`.
- **Shared contract** — one line, `Shared contract: see AGENTS.md`, instead of re-stating the
  scope gate, run-dir layout, guardrail rule, etc. in every body.
- **Tool-specific body** — Goal, Steps (the real commands), Modern tooling, a `## Checklist` of
  the tool-unique verifiable items, and tool-specific pitfalls.
- **Checklist** — a fenced `yaml` block of verifiable items (`verify: exists | nonempty |
  contains:<regex> | min-lines:<n> | exit-zero | judge`). The scope-confirmed item is always
  `on_fail: fail` and references inherited engagement `scope.json`. Paired events and unchanged native
  outputs distinguish a scoped empty result from a missing run; generated summaries are not proof.
- **Evidence writer** — skills call `scripts/otus-log.py` for scope checks, raw `run.log`, versioned
  `run.json` and `events.jsonl`, and rendered `findings.md`. Evidence goes under `$OTUS_HOME` or
  repository `out/`, grouped by engagement/tool/UTC timestamp; never under skill directories.

The behavioural rules every skill shares — task scope, evidence layout, the `run.json` schema,
guardrail handling, non-interactive execution, cleanup verification — live **once** in
[`AGENTS.md`](AGENTS.md).

## How to use it

Otus doesn't replace the tools — it drives them. You still need the underlying binaries
(nmap, subfinder, httpx, ffuf, nuclei, sqlmap, etc.) installed, e.g. on Kali or via each
tool's install docs.

1. **Verify runtime setup offline.** Check installed versions, discovery, exact worker names and
  resolved tool permissions using the startup checks in [docs/authoring.md](docs/authoring.md#32-runtime-discovery-and-startup-acceptance).
2. **Supply the task scope.** Give the target(s) or local artifact and an optional engagement name.
  The coordinator binds it automatically; no authorizer declaration or manually prepared record.
  Related tasks reuse that binding, and workers cannot enroll additional endpoints.
3. **Give a goal and checked inputs.** For an authorized HTB machine request actual user/root proof;
  for an assessment request minimal verified impact. The coordinator selects one finite skill/profile,
  invokes its exact owner, awaits terminal handback and independently reviews it before a next task.
4. **Collect evidence.** Raw results, structured records/events, and rendered findings land under
  the configured root. Use persistent storage or `otus-log.py archive --engagement "$ENGAGEMENT"`
  and retain a verified downloaded archive outside an ephemeral runtime before teardown.
5. **Review and report.** The locked reviewer checks actual bounded work, not an assumed full scan.
  The reporter compiles eligible individual findings, then that report is independently reviewed.

For example, port scanning starts with 100 TCP ports (or supplied ports), then light service detail
only on useful open ports. FFUF starts with <=100 contextual entries and 15 native seconds at low
load; no default recursive wordlist, full-port sweep or credential-dump ladder. Tool preflight and
health matter more than nominal speed. Thirty minutes is a progress checkpoint, not a solve guarantee
or automatic deadline; useful gains can justify finite extensions. Partial/unknown coverage and
missing flags stay explicit. See [AGENTS.md](AGENTS.md) for the shared allocation/stop rules.

## Runtimes

Otus is portable across agent runtimes. [`AGENTS.md`](AGENTS.md) is the single, runtime-agnostic
contract; the runtime-specific instruction files are **generated** from it.

- **Claude Code** discovers flat skills and native named workers on supported installed versions;
  verify actual registration/permissions, not only file presence. Other runtimes need the same
  acceptance checks; do not assume their agent/permission compatibility.
- **OpenCode v2** uses the generated `.opencode/agents/` profiles and project config, with `otus`
  as the default primary agent for new sessions. Start from the repository root and select `otus`
  explicitly in an existing session. The same 26 `.claude/skills/` files are discovered natively;
  workers reuse canonical `.claude/agents/` procedures, not a second framework. CLI commands use
  `shell`, never JavaScript `execute`; native `subagent` calls use the exact worker names.
  Provider/model settings remain yours, including Kali-to-LM-Studio connections. Capture literal
  installed versions and complete the [Kali acceptance checks](docs/authoring.md#34-kali-dual-runtime-acceptance)
  before claiming a tested runtime pipeline; local structural tests do not prove VM compatibility.
- **GitHub Copilot** uses native `.claude/skills/` and `.claude/agents/` discovery on supported VS Code
  versions. Select the generated [Otus coordinator](.github/agents/otus.agent.md), or built-in Agent
  with the same exact named delegation. No handoff button or generic-agent substitute. The generated
  contract is auto-included; do not invent a discovery setting.
- Reviewer has no execution; reporter assembly needs runtime-enforced restricted encode/concat/
  measure tools. If aliases resolve broadly or required tools are absent, setup fails closed; agents
  never widen permissions. In the tested VS Code 1.140.0 / Copilot 0.68.0 harness all four roles
  launched, but reporter shell assembly was unavailable. That is an acceptance gap, not report success.
  Reviewer could create a fresh verdict, not update an existing one; recovery acceptance needs a
  supported assigned-verdict writer. No separate native registration diagnostic was exposed.
- **Regenerate the adapters** after editing the contract:
  ```bash
  python3 -I scripts/build-runtimes.py   # contracts, Copilot coordinator and OpenCode profiles/config
  ```
  Edit `AGENTS.md` and canonical `.claude/agents/` procedures, never their generated adapters.
  OpenCode profiles inherit the configured model by omitting its model field; Claude's existing
  `model: inherit` metadata stays unchanged. No skill copies, shell plugin or model-specific tuning.

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

## Coordinator and workers

`CLAUDE.md` (generated) defines runtime routing, and `.claude/agents/` holds four subagents
that run selected skills in isolated contexts, also discovered natively by supported VS Code and
used as source bodies for generated OpenCode v2 workers:

- **`recon-runner`** — runs read-heavy recon/enumeration (subfinder, httpx, port-scanner, ffuf)
  and returns a concise summary instead of raw dumps.
- **`vuln-hunter`** — owns web/access/AD/privilege/RE/forensics tasks, one selected runbook per call.
- **`reviewer`** — evidence-read-only; independently verifies Checklist items, writes only assigned
  review.json, and returns PASS / FAILED-RECOVERED / FAILED / NON-COMPLIANT.
- **`reporter`** — reads the evidence root; compiles reviewed evidence into the final engagement
  report (canonical markdown plus a branded, self-contained HTML, print-ready via Save-as-PDF).
  Writes only under the configured engagement's report/.

The parent alone delegates and maintains private progress notes. Workers do not fork another skill,
start a reviewer or run a tool ladder. The canonical ownership table is in [AGENTS.md](AGENTS.md).

## Repository layout

```
AGENTS.md                        # the canonical, runtime-agnostic agent contract (edit this)
CLAUDE.md                        # GENERATED from AGENTS.md + Claude Code routing appendix
.github/copilot-instructions.md  # GENERATED from AGENTS.md + a Copilot note
.github/agents/otus.agent.md     # GENERATED coordinator; exact named-worker allowlist
.opencode/opencode.json         # GENERATED OpenCode v2 default; no provider/model override
.opencode/agents/               # GENERATED primary otus + the four canonical worker adapters
.claude/skills/<tool>/SKILL.md   # one capability per tool-named folder; the runbook the agent loads
.claude/agents/                  # recon-runner, vuln-hunter, reviewer, reporter subagents
docs/authoring.md                # skill-authoring + verification spec, tool catalog, conventions
docs/catalog.md                  # GENERATED human browse-index (by function + by domain)
templates/                       # SKILL.template.md, report.css
scripts/                         # generators, otus-log.py, test-otus-log.py
out/                             # timestamped run evidence, grouped by engagement (git-ignored)
```

## Docs

- [`AGENTS.md`](AGENTS.md) — the shared agent contract (task scope, evidence layout, `run.json`,
  guardrail handling, non-interactive execution, cleanup, self-report).
- [`docs/authoring.md`](docs/authoring.md) — skill format, metadata schema, the `## Checklist`
  verification spec, the tool catalog, the model/effort convention, and the build order.
- [`docs/catalog.md`](docs/catalog.md) — the generated browse-index of every skill.

## Maintainer

Otus is built and maintained by **Tom** ([@awt-tom](https://github.com/awt-tom)) of
[Security with Tom](https://securitywithtom.com) — home of Otus.
