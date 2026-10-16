# Otus — Skill & Agent Authoring Guide

> **What this is.** The single authoring reference for Otus skills. It merges the former
> `skill-generator-guide.md` (how to write a skill) and `skill-review-guide.md` (how skills are
> verified). Read it before adding or editing any skill.
>
> **The runtime contract lives in `AGENTS.md`, not here.** Scope gate, engagement workflow,
> evidence/run-dir layout, the `run.json` schema, platform-guardrail handling, non-interactive
> execution, target-host resolution, untrusted-target-content, cleanup verification, and self-report
> consistency are stated **once** in `AGENTS.md`. This guide never restates them — a skill body
> references them with the single line `Shared contract: see AGENTS.md`.
>
> **Task scope.** Every skill is for legitimate lab/authorized work. The parent automatically binds
> supplied targets or explicit offline work once in `<root>/<engagement>/scope.json` (see `AGENTS.md`).
> Skills inherit targeting context, not an authorization declaration or authorizer prerequisite.
>
> **Design basis:** goal-driven selection, bounded profiles and actual native evidence. Tool-specific
> defaults live in the owning runbooks; researched sources/rationale are linked in §5.14.

---

## 1. How the runtime uses a skill

1. At startup the agent **scans the skills directory** and injects only each skill's `name` +
   `description` into the system prompt.
2. The **`SKILL.md` body is NOT loaded** at this point — it stays on disk.
3. When an incoming task **matches a skill's description**, the agent pulls that skill into context by
   calling **`Read` on its `SKILL.md`** and then follows the body step-by-step.

**Design consequences:**

- **The `description` is the trigger.** It is the *only* thing the model sees when deciding whether to
  load the skill. Write it as "Use when…" packed with the words a user/agent would actually use (tool
  name + aliases + the task). A vague description = the skill never fires. Keep descriptions lean and
  triggery; put the depth in the body.
- **One concern per skill.** Prefer `nuclei`, `ffuf`, `sqlmap` as separate skills over one `web.md`.
- **The body is a runbook, not an essay** — exact command forms, decision points, output locations,
  and what to do with the results.
- **One task, useful handback.** Name proposed downstream work only as a coordinator handoff. A
  worker reads the selected runbook in its existing context, not another Skill/Agent fork. Direct
  invocation uses the same canonical owner; do not preload every skill or encode compulsory chains.

---

## 2. Skill metadata schema (frontmatter)

Put this YAML frontmatter at the top of every `SKILL.md`. The canonical shape is
`templates/SKILL.template.md` — copy it rather than hand-rolling.

```yaml
---
name: <tool>                      # lowercase/kebab-case; EQUALS the folder name
description: >                    # TRIGGER TEXT — "Use when <task>, with <tool + aliases>." Keyword-dense.
  One or two sentences so the matcher fires on the right requests and nothing else.
  Say when NOT to use it (name the sibling skill to prefer instead).
arguments: "<positional args>"    # required first, optional in [brackets]; keep to <= 3-4
model: inherit                    # ALWAYS 'inherit' (see §4) — never hardcode sonnet/opus/haiku/default
effort: low | medium | high       # by weight (see §4)
context: fork                    # direct invocation selects the canonical worker
agent: <owner>                   # exact role from AGENTS.md ownership table
background: false               # no dependent work before terminal handback
category: recon | web | access | ad-network | privesc-creds | re-forensics | meta
domain:   web | ad | network | host | crypto | binary | forensics | misc
---
```

| Field | Meaning | Guidance |
|---|---|---|
| `name` | Stable unique slug | Must equal the folder name; used in chaining references. |
| `description` | The match trigger | Highest-leverage field. Lead with the action; include tool name + synonyms. |
| `arguments` | Positional args | Required first, optional in `[brackets]`. Keep ≤ 3–4; everything else is a flag the body sets. |
| `model` | Model override | **Always `inherit`** — use the session model, never hardcode a name (see §4). |
| `effort` | Reasoning budget | Scale to how much *judgement* the task needs, not runtime (see §4). |
| `context` | Direct invocation routing | `fork`; a worker Read/executes without forking again. |
| `agent` | Canonical owner | Exact role from AGENTS.md, not Explore/general-purpose. |
| `background` | Awaited execution | `false`; late writes cannot feed dependent tasks. |
| `category` | Function group | One of the seven in §4; drives `docs/catalog.md` "By function". |
| `domain` | Target surface | One of the eight in §4; drives `docs/catalog.md` "By domain". |

Skills live **flat** at `.claude/skills/<tool>/SKILL.md` with **tool-named** folders (e.g.
`port-scanner`, `subfinder`, `ffuf`, `nuclei`, `review`). **No category subfolders** — no runtime
discovers nested skill dirs. Browse the full set in `docs/catalog.md` (generated by
`scripts/build-catalog.py`).

---

## 3. Using the template

Copy `templates/SKILL.template.md` and fill it in. The body is deliberately slim; the shared contract
is **not** restated in it. Sections, in order:

- `# <tool> — <one-line what-it-does>`
- **`Shared contract: see AGENTS.md`** — the one line that replaces the old per-skill boilerplate
  (scope-guard paragraph, run-dir anchoring, the `run.json` schema block, the generic guardrail note,
  "never write under skills/"). Do not re-state any of it.
- **`## Goal`** — what a successful run produces and why you'd reach for it (1–2 sentences).
- **`## Steps`** — numbered, executable: helper init, scope-check, helper-wrapped original command
  forms with finite native/helper budgets, decisions, triage and finish. Declare the actual profile
  and notes/task.md. Preserve native empty outputs unchanged; evidence/analysis proves results, not
  marker pollution. GUI steps save exports/events; review uses its locked writer exception.
- **`## Modern tooling & alternatives`** — current best-in-class, notable flags, legacy tools replaced.
- **`## Checklist`** — fenced YAML; the verification contract (spec in §8). First item is always the
  inherited `scope-confirmed` gate.
- **`## Notes / pitfalls`** — tool-specific gotchas only (rate limits, false positives, destructive
  flags to avoid, auth handling, which raw evidence to save to `loot/`).

**Never invent a flag.** Use the exact command forms from the catalog entry (§5); if a flag isn't
there, verify it against the tool's `--help` or official docs before writing it. A wrong flag is worse
than an omission. Keep each `SKILL.md` ≤ 75 lines.

### 3.1 Evidence helper and storage

The executable writer is `scripts/otus-log.py`, Python 3.12+ stdlib only on Linux/macOS; no network
client or third-party dependencies. Invoke from the repository root with `python3 -I` so local
module names/PYTHONPATH cannot shadow imports. Tool argv runs unchanged; only logging-only tees/spools
are replaced. Catalog command examples in §5 are tool argv references, not permission to bypass
the lifecycle in AGENTS.md. Real network tools are not required for the helper's self-tests.

| Subcommand | Role |
|---|---|
| `scope-init --engagement S --target T` | Parent binds supplied targets once; repeat target. Same normalized binding is idempotent; differing scope needs explicit user-approved replacement. Legacy authorizer/confirmed inputs are optional. |
| `scope-init --engagement S --offline` | Parent explicitly binds a purely local task without network targets. Cannot pass a remote endpoint check. |
| `scope-check --engagement S [--target T] [--targets-file FILE] [--run-dir DIR]` | Checks task binding and every endpoint; exits 0/2/3. Missing authorizer is not an error. With run-dir, denied checks write error handback. |
| `init --engagement S --skill NAME [--profile P] [--coverage-set C]` | Creates isolated partial record/events/raw log/findings; existing target/run-dir options remain. |
| `run --run-dir DIR [scope options] --timeout N --grace G [--outcome-policy P] -- CMD...` | Bounded process-group execution, raw capture and actual child/helper outcome metadata; policy in AGENTS.md. |
| `event --run-dir DIR --event marker --note M` | Records actual manual work; guardrail_stop with block/request-id finalizes the required stop handback. |
| `finish --run-dir DIR --status STATUS --summary S [--observed N] [--omitted O] [--stop-reason R]` | Finalizes actual task/coverage; repeated item/finding/handback flags and profile/set updates remain available. |
| `archive --engagement S [--out FILE]` | Creates a private tar.gz outside the engagement; refuses overwrite, symlinks, and recursive self-inclusion. |

`finish` accepts `--item 'id=ok|fail:evidence'` and
`--finding 'title=...;severity=...;evidence=...'`, with optional target/description/reproduction/remediation.
Use an evidence file for descriptions containing semicolons. Also supply observed `--target-state`
and `--cleanup`; verified cleanup needs `loot/cleanup_verify.txt`. Never paste secrets into summaries,
event notes, findings, or report text. Executable arguments are redacted from JSON; raw transcripts
and tool-native files remain private and may contain secrets. Record failures rather than treating
any nonzero as success; a terminal error may be enriched but never reopened.

The four canonical models live ONLY in AGENTS.md's **Versioned JSON models** section:
`otus/scope@1` (task binding, optional historical provenance), `otus/run@1` (run/findings/handback), `otus/event@1` (timeline),
and `otus/review@1` (independent verdict). Link to them; do not copy schema definitions into skills.
Standalone review writes its verdict through the reviewer-role exception; locked reviewer/report
agents never invoke Python. Their direct Write outputs follow the same models and are independently
checked. Legacy evidence remains untouched and excluded until independently reviewed.

Evidence root is `OTUS_HOME` or repository `out/`; it is per engagement, not per session. A custom
root must also be outside tracked files (add a local ignore if necessary); never commit evidence.
For ephemeral Codespaces/Claude runtimes, mount persistent storage or export before teardown:

```bash
python3 -I scripts/otus-log.py archive --engagement "$ENGAGEMENT" --out /persistent/path/evidence.tar.gz
tar -tzf /persistent/path/evidence.tar.gz
```

Download an archive made inside an ephemeral runtime, extract it in a private directory, verify
scope/run/event/review/raw evidence is present, and retain it outside the runtime. Restore the original
mounted evidence path when resuming absolute run_dir records. For relocated archives, disclose original
paths during read-only review; do not rewrite source records silently. An archive still inside a
disposable runtime is not durable. Stop active runs before archiving for a consistent snapshot.
JSON replacement is atomic, but multi-file writes/teardown cannot be made transactional by instructions;
an unfinished partial record is never promoted to complete.

Verification: `python3 -I scripts/test-otus-log.py` uses synthetic fixtures/temp directories,
covering scope gates, failures/signals, raw output, ordering, escaping, archive restoration, and
skill/agent wiring. After a contract or routing edit, run `python3 -I scripts/build-runtimes.py`;
the first generation changes contracts/coordinators/OpenCode profiles, and a second generation
must produce no additional diff. Valid historical scope/evidence files are never migrated.

### 3.2 Runtime discovery and startup acceptance

Use offline read-only setup checks before an engagement; these are not skill runs and create no scope
or engagement evidence. Check installed runtime/extension versions and supported native discovery,
then actual role registration, parent agent tool, skill frontmatter and resolved worker capabilities.
Supported VS Code can load `.claude/agents/*.md` directly; absence of duplicated `.github` worker files
is not proof of failure. The generated `.github/agents/otus.agent.md` is the coordinator entrypoint.

1. Refresh discovery using the installed runtime's supported UI/diagnostics. Confirm all 27 skill
  names and exact four worker names, not merely files. Verify the coordinator's agent tool/allowlist.
2. Invoke each exact named role with an offline-read-only setup task: read its definition/contract,
  return registered identity and actual available tools, no shell/targets/writes/delegation. At most
  two independent checks concurrently. Missing role/delegation controls -> setup failure, no fallback.
3. Reviewer must resolve no execution. Reporter encode/concat/measure permissions must be enforced,
  not inferred from `Bash(pattern)` strings; broad or absent execution cannot pass assembly acceptance.
  Check assigned verdict creation and any required replacement separately: create-only Write cannot
  update an existing verdict. Extra resolved tools must be disclosed; aliases are not a filesystem
  or child-delegation sandbox, and do not authorize use beyond the role contract.
4. In an isolated synthetic/temp-root test (no security tools or real targets), check terminal
  execution -> exact reviewer verdict artifact -> reporter compilation -> independent report review.
  Inspect actual outputs/handbacks; don't promote a startup echo or mocked run as completed acceptance.
5. If a stage is unavailable, disclose the precise gap and stop that stage without changing tools,
  permission modes or settings. Recheck named roles after user-driven supported setup changes.

Local setup observation: VS Code 1.140.0 / Copilot 0.68.0 launched all four exact roles by named calls;
no separate registration diagnostic was exposed. Reviewer had no execution and create-only verdict
writing; reporter had no shell, so report assembly/end-to-end acceptance remains blocked.
This is a tested-harness limitation, not a portable minimum version or an instruction to widen tools.

### 3.3 OpenCode v2 adapter

The adapter targets documented **v2**, not v1 `permission`/`bash`/`task` configuration. Obtain
literal `opencode --version`, `opencode --help` and `claude --version` output from Kali; a model's
self-description or the website's download version is not an installed-version check. The local
suite verifies generated structure, not an installed Kali release or actual permission enforcement.

Start OpenCode at the repository root with a new session, or select `otus` explicitly in an existing
session. `.opencode/opencode.json` chooses only the default agent; it does not change provider,
model, endpoint, credentials or global permissions. Keep local/cloud/LM Studio configuration in
the user's existing setup, including the VM-to-host connection. No model-specific tuning or plugin.

`scripts/build-runtimes.py` generates `otus` plus exact `recon-runner`, `vuln-hunter`, `reviewer`
and `reporter` Markdown profiles. Canonical worker procedures remain under `.claude/agents/`.
OpenCode discovers the same `.claude/skills/<name>/SKILL.md` files, strips their frontmatter on
load, and does not dispatch Claude `context: fork`/`agent` metadata. The parent routes to the owner;
workers Read the selected original runbook in their existing context. Do not copy skills or route
an internal IP through subfinder. Missing named registration fails setup without a generic fallback.

Generated system bodies carry the runtime mapping directly because v2's accepted `instructions`
config currently does not load its entries. V2 reads shared AGENTS.md, not a CLAUDE.md fallback.
OpenCode model fields are omitted to inherit the configured session model; Claude metadata and
its native routing/tool names remain unchanged.

Use direct foreground `shell` for CLI/OS commands; `execute` is JavaScript Code Mode and is denied
for these Otus profiles, not globally. Use `subagent` foreground calls and await terminal handbacks.
Set shell `workdir` to the repo root; each call is fresh, so pass environment and absolute run paths
explicitly. Shell timeout uses **milliseconds**, helper timeout/grace use seconds. The outer timeout
must exceed `(helper timeout + grace + 30) * 1000` to allow shutdown and evidence flushing; for a
120-second helper and five-second grace, use at least 155000 ms. Keep helper-native finite bounds
and non-interactive/closed-stdin rules; an outer timeout is still a failure, never a successful scan.

Permissions use ordered v2 `action`/`resource`/`effect` rules, last match wins. Workers cannot launch
subagents; reviewer has no shell/network and may write verdicts only; reporter allows only the
canonical local encode/concat/measure commands. Static path rules cover repository `out/`; exact
assigned engagement/run paths remain a role contract, not a filesystem sandbox. Shell command
scanning is best effort and cannot prove filesystem or network confinement.

For an external/custom OTUS_HOME, retain only user-approved boundaries. Generated profiles do not
silently grant external-root access; actual read/edit/external-directory permissions must resolve
for that root and assigned role. Inspect merged project/global/managed rules and saved approvals.
Never widen permissions or switch settings automatically. Broad or unenforceable reporter shell
permissions stop assembly, and missing verdict replacement support is disclosed separately.

Official v2 references: [agents](https://opencode.ai/v2/docs/agents),
[tools](https://opencode.ai/v2/docs/tools), [permissions](https://opencode.ai/v2/docs/permissions),
[skills](https://opencode.ai/v2/docs/skills), [config](https://opencode.ai/v2/docs/config) and
[instructions](https://opencode.ai/v2/docs/instructions). Recheck these against the installed version.

### 3.3.1 HexStrike MCP server config

`scripts/build-runtimes.py` also emits the HexStrike AI MCP wiring from one definition so both runtimes
stay aligned: Claude Code `.mcp.json` (stdio bridge `hexstrike_mcp.py --server <url>`), the OpenCode
`.opencode/opencode.json` `mcp.servers.hexstrike` entry, and `.claude/settings.local.json`. All three
are generated local runtime config (gitignored, like `.opencode/opencode.json`); regenerate them per
environment. The bridge path/python/URL come from `HEXSTRIKE_HOME`, `HEXSTRIKE_PYTHON` and
`HEXSTRIKE_SERVER` (placeholder defaults `/opt/hexstrike-ai`, `.../hexstrike-env/bin/python3`,
`http://127.0.0.1:8888`) resolved at generation time, so no real host/path is committed.

The OpenCode server sets `codemode: false` because every Otus role denies `execute`/Code Mode; without
it OpenCode would route MCP tools through Code Mode and they would be unreachable. Access is curated:
each worker's canonical `tools:` frontmatter lists its `mcp__hexstrike__<tool>` set (Claude Code), which
the generator maps to OpenCode `<server>_<tool>` allow rules; `otus` inherits the union; `reviewer` and
`reporter` get none. Widen only by editing that frontmatter and regenerating. HexStrike tool calls are
not shell commands the helper can wrap — they run through the `hexstrike` skill, which `scope-check`s the
target, records each call with `otus-log.py event --event marker`, and saves raw output under `evidence/`,
producing one evidence trail identical in both runtimes. Verify with `python3 -I scripts/test-otus-log.py`.

### 3.4 Kali dual-runtime acceptance

Run the local synthetic suite and generator consistency checks first. Then the operator runs all
seven checks in Kali, retaining actual tool traces and private evidence references. Capture literal
versions and the current Claude baseline before testing OpenCode. Do not use a historical lab IP
without selecting the currently assigned instance; no target contact is needed for negative checks.

1. **Claude regression:** existing named-worker/direct-skill flow and bounded concurrent independent
  tasks still produce terminal evidence, independent verdicts, report and report review. Only
  target-only initialization differs; no Claude tool/fork/metadata change.
2. **Basic execution:** a normal Nmap service-scan request for the supplied lab target selects direct
  `shell` without user reminders. Inspect actual helper/Nmap events/native output; no Code Mode or
  "Unexpected token" result. Generated prompts are not proof of correct tool selection.
3. **Named delegation:** `otus` actually launches exact `recon-runner` with one bounded port-scanner
  profile and inherited inputs, awaits its terminal handback, then invokes the independent reviewer.
  File presence or an Explore/general substitute cannot satisfy registration.
4. **Shared skills:** both runtimes discover all 27 IDs and read the same canonical skill paths/bodies.
  No duplicate skill directory or provider-specific corpus; Claude fork metadata is not v2 routing.
5. **No authorization prerequisite:** in an isolated evidence root, a target-only task automatically
  binds scope and starts permitted work with no authorizer declaration, record or confirmation flag.
  Also check explicit offline artifact binding without an invented endpoint.
6. **Target propagation:** inherited engagement/root/target remain identical through coordinator,
  worker, helper and native output. Synthetic mixed/outside targets and unchecked redirects stop
  before contact; child scopes never enroll new endpoints. Do not probe an outside live target.
7. **Evidence pipeline:** real terminal run.json, ordered paired events, raw log/native output and
  matching findings.md lead to a fresh independent review.json, eligible markdown/self-contained
  HTML report and report review. Check verdict replacement, default/custom approved evidence roots,
  isolated concurrency, and truthful error/refusal records with no dependent continuation.

Record PASS/FAIL/unavailable per check, actual versions, evidence paths, omissions and cleanup owed.
Unsupported stages are acceptance gaps, not success. Only all seven actual checks justify claiming
a tested dual-runtime pipeline; the no-network local suite and static permission checks cannot.

---

## 4. Model / effort convention (normative)

Portability rule: **nothing hardcodes a model name** that may not exist in another runtime.

- **`model: inherit`** in **every** `.claude/skills/*/SKILL.md` **and** every `.claude/agents/*.md`.
  Use the session's model everywhere; never pin `sonnet`/`opus`/`haiku` (and never `default`, which
  errors with "model may not exist").
- **`effort` by weight:**

  | Group | Skills | effort |
  |---|---|---|
  | recon | `subfinder`, `httpx`, `port-scanner`, `ffuf` | **low** |
  | web / access / ad-network / privesc-creds | `burpsuite`, `nuclei`, `sqlmap`, `xss`, `idor`, `ssrf`, `exploitation`, `metasploit`, `hydra`, `ssh-foothold`, `bloodhound`, `netexec`, `impacket`, `linpeas`, `privesc-root`, `hashcat` | **medium** |
  | re-forensics | `binwalk`, `steghide`, `wireshark` | **medium** |
  | re-forensics (deep reasoning) | `ghidra`, `pwntools` | **high** |
  | meta | `review` | **high** |

  **Agents:** `recon-runner` → low · `vuln-hunter` → medium · `reviewer` → high · `reporter` → medium.

- Match `context: fork`, `agent` and foreground handback to the canonical routing, not old generic
  catalog defaults. Runtime metadata support must be checked; prose/frontmatter alone is not enforcement.

**`category` / `domain` assignment** (one each, from the skill's real target):

| Skill | category | domain |
|---|---|---|
| subfinder, httpx, port-scanner, ffuf | recon | network (port-scanner) · web (subfinder/httpx/ffuf) |
| burpsuite, nuclei, sqlmap, xss, idor, ssrf | web | web |
| exploitation, metasploit, ssh-foothold | access | host |
| hydra | access | network |
| bloodhound, netexec, impacket | ad-network | ad |
| linpeas, privesc-root | privesc-creds | host |
| hashcat | privesc-creds | crypto |
| ghidra, pwntools | re-forensics | binary |
| binwalk, steghide, wireshark | re-forensics | forensics |
| review | meta | misc |

Canonical ordering for generated indexes — **category:** recon, web, access, ad-network,
privesc-creds, re-forensics, meta; **domain:** web, ad, network, host, crypto, binary, forensics,
misc. Do **not** add any ATT&CK/MITRE field to frontmatter.

---

## 5. Tool catalog — bug bounty & CTF/HTB

Organized by capability, not a compulsory phase sequence. Examples below are selected initial argv;
the owning runbook is authoritative for current version/profile, helper caps, evidence and finish.
Broad/deep variants are conditional escalations requiring a lead or explicit coverage objective.
Companions run only inside a selected worker task, not new implicit skills/delegates. Metadata uses
`effort · fork · canonical-owner`; the ownership table itself lives only in AGENTS.md.

### 5.1 Reconnaissance & subdomain enumeration

#### `subfinder` — passive subdomain discovery `low · fork · recon-runner`
- **Goal:** A bounded passive list for a relevant apex-domain objective; skip isolated internal IP/HTB discovery.
- **Steps:** version/source preflight -> `subfinder -d "$domain" -silent -timeout 5 -max-time 1 -o subs.txt` (one native minute, helper 75 seconds) -> actual source coverage/clean deduplicated handoff. All-source/recursive/extra-tool merging needs a new lead/allocation.
- **Modern tooling:** ProjectDiscovery standard; pair with `amass` (more thorough, slower) and `assetfinder`. Legacy `sublist3r` is largely superseded.
- **Output formats:** plaintext list; `-oJ` for JSON lines.
- **Notes:** Passive only — low noise, safe default. Rate-limit API sources via config.

#### `httpx` — HTTP probing & fingerprinting `low · fork · recon-runner`
- **Goal:** From a host list, find which are live over HTTP(S) and capture title, status, tech, IP, CDN — the "what's actually reachable" filter.
- **Steps:** verify ProjectDiscovery binary/alias before contact -> explicit URL batch with `-json -threads 5 -rate-limit 10 -timeout 5 -retries 0 -no-fallback-scheme` (helper 60 seconds) -> derive clean scheme/port URLs -> <=3 goal-relevant page observations. No unchecked redirects or automatic crawler/scanner handoff.
- **Modern tooling:** ProjectDiscovery `httpx` (not the Python `httpx` lib). Replaces `httprobe` + manual `curl` loops.
- **Output formats:** plaintext / `-json` (JSONL with tech, status, title).
- **Notes:** `-rate-limit` to stay polite; respect program rate rules.

#### `nmap` (`port-scanner`) — port & service scanning `low · fork · recon-runner`
- **Goal:** Enumerate open ports, services, and versions on a host; the backbone of every HTB box and network-scope recon.
- **Steps:** selected `nmap -sT --top-ports 100 -oA scans/initial "$target"` (helper 120 seconds), or supplied ports -> parse XML -> light `-sV --version-light` on useful open ports only. Remaining top-1000/full TCP is a recorded lead-driven escalation in finite chunks, not a first task; selected NSE is separately bounded.
- **Modern tooling:** Nmap is the baseline; faster scanners are alternatives for a justified coverage need, not an extra mandatory pass.
- **Output formats:** `-oA` emits normal/greppable/XML at once; XML → `searchsploit --nmap` and reporting.
- **Notes:** No forced minimum rate. Host-timeout may discard port tables; XML native accounting distinguishes filtered/down/skipped from scanned negatives. Unselected TCP/UDP remain omitted.

**Companion recon tools (bundle into the skills above):**

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

### 5.2 Content discovery & fuzzing

#### `ffuf` — web fuzzer (dirs, files, params, vhosts) `low · fork · recon-runner`
- **Goal:** Discover hidden paths, files, parameters, and virtual hosts on a web target.
- **Steps:** map known pages/three distinct invalid controls -> <=100 contextual entries with `-t 5 -rate 10 -timeout 3 -maxtime 15 -noninteractive -se -mc all -of json` (helper 35 seconds) -> native coverage/health -> <=3 candidate comparisons. Only healthy useful progress justifies <=400 additional entries/45 native seconds; larger/recursive/vhost modes are new tasks with checked endpoints.
- **Modern tooling:** `ffuf` and `feroxbuster` are the current standard; `gobuster` still common. Legacy `dirb`/`dirbuster`/`wfuzz` superseded.
- **Output formats:** `-of json|csv|html|md`; default stdout.
- **RAG / cross-skill:** **Heavily wordlist-driven** — see §7 (SecLists). Feeds vuln skills (LFI, upload, IDOR) and Burp.
- **Notes:** Preserve empty JSON; `-se` is not an aggregate error-rate check. Record unfinished native budgets as partial and update metadata to actual pilot/followup sets.

**Companion discovery tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `feroxbuster` | Recursive content discovery (fast, Rust) | txt / json | medium · fork |
| `gobuster` | Dir/dns/vhost brute (simple, fast) | txt | low · inline |
| `dirsearch` | Dir brute with smart extensions | txt / json | low · inline |
| `wpscan` | WordPress enum + vuln + user/pw | cli / json | medium · inline |

### 5.3 Vulnerability scanning

#### `nuclei` — template-based vulnerability scanner `medium · fork · vuln-hunter`
- **Goal:** Scalable, low-false-positive detection of known CVEs, misconfigs, exposures, and takeovers across many hosts using community + custom templates.
- **Steps:** verified cached <=20 relevant template paths, no per-target update/clone -> `-c 2 -bs 1 -rate-limit 10 -timeout 5 -retries 0 -mhe 5 -dr -ni -duc -jsonl` (helper 180 seconds) -> native skip/health assessment -> minimum verification/triage. No code/headless/DoS/brute/fuzz or unchecked OOB defaults.
- **Modern tooling:** Use reviewed compatible template caches; updates are separate setup work.
- **Output formats:** plaintext; `-json`/`-jsonl` for pipelines; `-markdown-export` for reports.
- **RAG / cross-skill:** **Strong RAG fit** — index the template library + CVE notes. Consumes `httpx` live list; feeds manual verification and reporting.
- **Notes:** `-rate-limit` / `-c` concurrency to stay in bounds. Triage is mandatory — never report raw nuclei output.

**Companion scanning tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `nikto` | Web server misconfig/legacy checks | txt / xml / csv | low · inline |
| `dalfox` | XSS discovery & verification | txt / json | medium · inline |
| `testssl.sh` | TLS/SSL config auditing | txt / json / csv | low · inline |

### 5.4 Manual web testing & exploitation

#### `sqlmap` — SQL injection detection & exploitation `medium · fork · vuln-hunter`
- **Goal:** Confirm and exploit SQLi, then extract data / escalate (DBMS fingerprint, dump, read files, shell) on an authorized target.
- **Steps:** stable captured request/selected parameter -> `sqlmap -r "$REQ" -p "$PARAM" --batch --level 1 --risk 1 --threads 1 --timeout 5 --retries 0 --ignore-redirects --output-dir "$RUN/sqlmap-output"` (helper 120 seconds) -> actual traffic/confirmation. Data enumeration/extraction, higher risk/level or OS/file/tamper actions are separate justified tasks, not checklist requirements.
- **Modern tooling:** `sqlmap` still standard for automated SQLi; `ghauri` is a faster newer alternative. For manual blind SQLi, hand-crafted payloads + Burp.
- **Output formats:** CLI tables; session/logs under `~/.local/share/sqlmap/output/<host>/`; `--dump-format=csv`.
- **RAG / cross-skill:** Pairs with a SQLi payload/tamper RAG (PayloadsAllTheThings). Input often from `ffuf`/Burp-found params. **Banned in OSCP exam** — note that in the body if relevant.
- **Notes:** `--batch` for non-interactive; cap `--level/--risk`; **never** `--dump` entire DBs by default — minimise data pulled.

#### `burpsuite` — intercepting proxy & web testing platform `medium · fork · vuln-hunter`
- **Goal:** Manually intercept, inspect, modify, and replay HTTP(S); the hub for authz testing, Repeater-driven exploitation, and Intruder fuzzing.
- **Steps:** one mapping/replay/export hypothesis, 300-second task -> actual scope-restricted GUI observations/controlled Repeater cases -> raw exports/events. No broad crawler/Intruder ladder; unavailable GUI means partial/manual handback, not invented work.
- **Modern tooling:** Burp Suite (Pro for active scan/extensions; Community for manual). `Caido` is a fast-growing lighter alternative; OWASP `ZAP` is the open-source option.
- **Output formats:** Burp project file; exported report (HTML/XML); copied requests.
- **Notes:** GUI tool — the skill is mostly a *methodology checklist* plus request/response handling, rather than a single command.

### 5.5 Exploitation frameworks & exploit lookup

#### `metasploit` (`msfconsole`) — exploitation framework `medium · fork · vuln-hunter`
- **Goal:** Select/configure/run exploit or auxiliary modules, deliver payloads, and manage sessions/post-exploitation.
- **Steps:** one matched module/options -> one-shot `msfconsole -q -x "use ...; set ...; check; exit"` (helper 120 seconds) -> inspect terminal check -> separate justified one-shot run/proof (<=120 seconds). No combined check/run, interactive session, migration or indefinite handler; unsupported check needs actual applicability evidence.
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

### 5.6 Active Directory & lateral movement (HTB/OSCP core)

#### `netexec` (`nxc`, formerly CrackMapExec) — network/AD swiss-army knife `medium · fork · vuln-hunter`
- **Goal:** Authenticate and enumerate/act across SMB/WinRM/LDAP/MSSQL/RDP at scale — spray creds, enumerate shares/users, run modules (LAPS, GPP, kerberoast), confirm access.
- **Steps:** selected known protocol/identity and checked endpoints -> serial auth/query with helper 60 seconds -> distinct credential/privilege/resource proof and actual/unknown lockout effects. Null/guest, RID, modules and protocol pivots are alternative lead-driven tasks; no compulsory ladder/spray.
- **Modern tooling:** `netexec` is the maintained fork — use it over the retired `crackmapexec`.
- **Output formats:** colorized CLI; loot DB under `~/.nxc/`; `--log` to file.
- **RAG / cross-skill:** Feeds and is fed by BloodHound + impacket. A WADCOMS/AD-attack RAG maps "I have X → do Y".
- **Notes:** Account lockout risk on spraying — check policy, throttle, prefer `--continue-on-success` deliberately.

#### `bloodhound` (+ `bloodhound-python` / `SharpHound`) — AD attack-path analysis `medium · fork · vuln-hunter`
- **Goal:** Collect AD objects and reveal privilege-escalation / lateral-movement paths to high-value targets (e.g. Domain Admin).
- **Steps:** one AD hypothesis/supported compatible collector, targeted directory methods such as Group,ACL and checked DC/GC/DNS endpoints (helper 180 seconds) -> real objects/import receipt/query results -> candidate path, not exploitation proof. Recollection requires a recorded relevant topology/permission/membership change; no default All/session discovery.
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

### 5.7 Password attacks

#### `hashcat` — GPU password/hash cracking `medium · fork · vuln-hunter`
- **Goal:** Recover plaintext from captured hashes to enable auth/lateral movement.
- **Steps:** provenance/source-confirmed mode/backend -> one finite contextual dictionary, native `--runtime 60 --status --status-json` (helper 90 seconds), isolated session/restore/pot/output -> actual status/exit/recovery assessment -> input/pot-only show. Rules/masks require a specific pattern/new finite task; no default ladder.
- **Modern tooling:** `hashcat` (GPU) is primary; `john` for format coverage/CPU and jumbo scripts (`*2john`). `name-that-hash` for ID.
- **Output formats:** private per-run pot/restore/outfile and native final JSON; no unrelated default-pot reuse.
- **RAG / cross-skill:** A hash-mode lookup table + rules/mask cheat-sheet RAG saves time. Consumes hashes from `responder`/`secretsdump`/web dumps; feeds `netexec`/login skills.
- **Notes:** Only verified v6.2.6 direct argv supports expected-nonzero policy: exhaustion may recover hashes; native runtime is partial, unsupported/contradictory evidence stays strict error.

**Companion password tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `john` (Jumbo) | CPU cracking + `*2john` converters | potfile / `--show` | medium · inline |
| `hydra` | Online login brute (ssh/ftp/http-form/…) | txt | medium · inline |
| `wordlists` (rockyou, SecLists, CeWL, mentalist) | Candidate generation | files | — (shared data) |

### 5.8 Service enumeration (per-port, HTB staple)

**These usually belong inside `nmap`-branching or small per-service skills.**

| Tool | Service | Role | Output | Default |
|---|---|---|---|---|
| `enum4linux-ng` | SMB/NetBIOS | Users/shares/policy enum (JSON/YAML export) | txt / json / yaml | low · inline |
| `smbclient` / `smbmap` | SMB | List/access shares, check perms | cli / txt | low · inline |
| `snmpwalk` / `onesixtyone` | SNMP | Community strings, MIB walk | txt | low · inline |
| `ldapsearch` | LDAP | Directory enumeration | ldif / txt | low · inline |
| `redis-cli` / `mongo` etc. | DB services | Unauth access checks | cli | low · inline |

### 5.9 Privilege escalation & post-exploitation

#### `linpeas` / `winpeas` (PEASS-ng) — automated privesc enumeration `medium · fork · vuln-hunter`
- **Goal:** Surface likely local privilege-escalation vectors on a compromised host (SUID, caps, cron, creds, misconfigs, kernel).
- **Steps:** reuse/cheap selected host context -> PEASS only for an unresolved useful gap, reviewed staged artifact/remote-native cap/helper 180 seconds -> <=3 actual prerequisite cross-checks. No download-to-shell/default all-checks/remote output file; positive cleanup proof for staged artifacts. Return candidates, never execute privesc here.
- **Modern tooling:** PEASS-ng `linpeas.sh` / `winPEASx64.exe`. Companions: `pspy` (process watch, no root), `linux-exploit-suggester`, `wesng` (Windows).
- **Output formats:** unchanged local raw stdout/context and separate vector/coverage analysis.
- **RAG / cross-skill:** **GTFOBins + LOLBAS + HackTricks privesc = ideal RAG.** Runs after any initial foothold skill.
- **Notes:** Noisy/slow — fine in labs, think twice in sensitive environments. Don't blindly run suggested exploits; verify first.

**Companion privesc/post tools:**

| Tool | Role | Output | Default |
|---|---|---|---|
| `pspy` | Watch cron/processes without root | stdout | low · inline |
| `linux-exploit-suggester` / `wesng` | Map kernel/OS to known exploits | txt | low · inline |
| GTFOBins / LOLBAS (reference) | "This binary → this escalation" | lookup | — (RAG data) |

### 5.10 CTF — binary exploitation & reverse engineering

#### `pwntools` — exploit development framework (Python) `high · fork · vuln-hunter`
- **Goal:** Script interaction with local/remote binaries and build working pwn exploits (I/O, packing, ROP, shellcode, format-string).
- **Steps:** one reproducible local-first hypothesis, total task 300 seconds -> captured offsets/leaks/binary/libc facts -> finite script attempts with I/O deadlines and close -> conditional checked remote proof (helper 60 seconds). No debugger attachment/interactive/unbounded receive or automatic remote replay.
- **Modern tooling:** `pwntools` + `gdb` with `pwndbg` or `GEF`; `ROPgadget`/`ropper`; `one_gadget`; `angr` for symbolic execution; `checksec`.
- **Output formats:** the exploit script itself + captured flag; structured logs via `context.log_level`.
- **RAG / cross-skill:** A pwn-technique RAG (ret2libc, ret2csu, ret2dlresolve, heap notes) + prior writeups is very useful. Pairs with `radare2`/`ghidra` for the static side.
- **Notes:** Highest-reasoning skill class. Iterate local-first; keep offsets/leaks reproducible.

#### `ghidra` — reverse engineering suite (decompiler) `high · fork · vuln-hunter`
- **Goal:** Statically understand an unknown binary — decompile to C-like pseudocode, map logic, find the check/flag/vuln.
- **Steps:** cheap triage/string/xref lead -> selected functions, native headless `-analysisTimeoutPerFile 240` below helper 300 seconds if needed -> actual log/project/logic exports cross-checked with disassembly. Directory existence is not analysis; native timeout can exit zero but remains partial.
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

### 5.11 CTF — forensics, stego & network

#### `wireshark` / `tshark` — packet analysis `medium · fork · vuln-hunter`
- **Goal:** Extract secrets/flags/artifacts from a pcap — follow streams, carve files, decode protocols.
- **Steps:** offline protocol sample with `tshark -n -c 10000` (helper 60 seconds, task 120) -> <=3 selected streams/artifacts -> actual filtered subset before object export -> coverage/secret-free artifact refs. Preserve original PCAP; no assumed whole-capture negative or external name resolution.
- **Modern tooling:** Wireshark GUI + `tshark` for scriptable/headless extraction; `tcpdump` to capture; `NetworkMiner` for artifact carving.
- **Output formats:** carved files (Export Objects), `tshark -T fields/-T json` for structured, CSV.
- **Notes:** Prefer `tshark` for automation inside a skill; huge pcaps → filter first.

#### `binwalk` — firmware/file carving & analysis `medium · fork · vuln-hunter`
- **Goal:** Detect and extract embedded/hidden files within a blob (firmware, image, odd file) — classic forensics/stego first move.
- **Steps:** signature first (helper 60 seconds) -> selective credible container extraction only -> enforce actual <=2 layers/100 files/100 MiB before recursion -> inspect offsets/content without execution/path escapes. Unsupported enforcement means skip/disclose, not invented limit flags or unlimited recursion.
- **Modern tooling:** `binwalk` (v3 Rust rewrite); companions `foremost`/`scalpel` (carving), `file`/`strings`, `bulk_extractor`.
- **Output formats:** extraction dir `_<file>.extracted/`, signature report (stdout / log).
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

### 5.12 CTF — crypto & misc

| Tool | Role | Output | Default |
|---|---|---|---|
| `CyberChef` | Encoding/decoding/crypto swiss-army (recipes) | transformed data | low · inline |
| `z3` (solver) | Constraint solving (rev/crypto) | model/solution | xhigh · inline |
| `sage` / `python+pycryptodome` | Math/crypto attacks (RSA, ECC, lattices) | script output | xhigh · inline |
| `RsaCtfTool` | Automated RSA weaknesses | key/plaintext | high · inline |
| `hashid` / `name-that-hash` | Identify hash/encoding types | txt | low · inline |

### 5.13 Secrets & source review (bug bounty)

| Tool | Role | Output | Default |
|---|---|---|---|
| `trufflehog` | Verified secret scanning (git/repos/filesystems) | json / txt | medium · inline |
| `gitleaks` | Fast secret detection in git history | json / sarif | low · inline |
| `gf` + patterns | grep-powered pattern hunting over URLs/JS | txt | low · inline |
| `LinkFinder` / `getJS` | Pull endpoints/secrets from JS | txt | low · fork |

### 5.14 Researched choices and limits

Otus borrows selective service-triggered routing from [AutoRecon](https://github.com/AutoRecon/AutoRecon),
explicit modes/resume discipline from [reconFTW](https://github.com/six2dez/reconftw), and maintained
reasoning/execution/result context from [PentestGPT](https://github.com/GreyDGL/PentestGPT).
[OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/) informs risk/objective-led
verification. These are design references, not imported exhaustive chains or benchmark guarantees.

Version-specific checks informing these defaults: [Nmap timing](https://nmap.org/book/man-performance.html)
(host timeout can discard results); [FFUF v2.1.0](https://github.com/ffuf/ffuf/tree/v2.1.0)
(native timebox/flush and consecutive-error semantics); [Hashcat v6.2.6](https://github.com/hashcat/hashcat/tree/v6.2.6)
(native status JSON and exit semantics). Flags/classifiers must still match installed help/source.
[VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents) and
[Claude Code subagents](https://code.claude.com/docs/en/sub-agents) describe discovery/permission
features; local resolved tools and actual named startup calls, not examples alone, decide support.

---

## 6. Vuln-category skills — "cut it down"

When the thing you're writing isn't a *tool* but a *vulnerability class*, **do not write one giant
`web-vulns.md`.** Split it into narrow, independently-triggerable skills. A granular skill matches
precisely and loads a focused runbook; a broad one matches everything and helps with nothing.

| Skill | Triggers on | Core body |
|---|---|---|
| `sqlmap` | SQL injection, union/blind/error | detection flow → manual payloads → sqlmap tuning → extraction minimisation |
| `xss` | reflected/stored/DOM XSS, dalfox | context analysis → payloads per sink → confirm → impact PoC |
| `ssrf` | server-side request forgery | <=3 fetch candidates, checked controlled destination, minimum correlated proof; no default metadata sweep |
| `idor` / `bola` | broken object/access control | <=3 controlled A/B object/action pairs, ownership comparison and authz matrix |
| `lfi-rfi` | file inclusion, path traversal, php wrappers | payload ladder → wrappers/log poisoning → RCE path |
| `file-upload` | upload bypass, webshell | extension/content-type/magic bypass → execution |
| `ssti` | template injection | detect polyglot → identify engine → sandbox escape → RCE |
| `auth` | login/session/JWT/OAuth flaws | session fixation, JWT (`jwt_tool`), reset flows, MFA bypass |
| `xxe` | XML external entity | entity injection → file read/SSRF → OOB |
| `cmd-injection` | OS command injection | detection → separators → blind/OOB confirm |

**Rules for vuln-category skills**
- **One class per skill.** If a body grows a second "## Also check…" class, split it.
- **The body is a focused testing methodology** with selected cases and proof/stop criteria. Name
  proposed other skills in the handback; workers never invoke or chain skills themselves.
- **Lean on RAG hard here:** point each at the relevant **PayloadsAllTheThings** folder +
  **HackTricks** page so payload libraries live in the RAG store, not hardcoded in the body.
- **`effort` follows §4** (web class = medium); the bypass-heavy reasoning stays in the methodology.

---

## 7. Shared data, RAG & cross-skill wiring

Several skills are far stronger when backed by a **shared data layer** rather than duplicating
content. Set these up once and have skills reference them.

**Shared wordlists / payloads (not per-skill copies):**
- `SecLists` — the canonical wordlist collection. Pin a path; let `ffuf`/`feroxbuster`/`gobuster`
  reference it.
- `PayloadsAllTheThings` — payloads per vuln class. Ideal RAG source for the §6 skills.
- Reviewed cracking dictionaries/rules as optional sources; select a finite contextual subset/pattern,
  not automatic `rockyou.txt`/rules ladders.

**RAG stores that give real uplift (index these):**
- **HackTricks** — methodology per service/OS/privesc/AD. Broadly useful.
- **GTFOBins / LOLBAS / WADCOMS** — "living-off-the-land → escalation" lookups for privesc & AD.
- **nuclei-templates** index + CVE notes — template selection/authoring.
- **CWE/OWASP + PayloadsAllTheThings** — for vuln-category skills.
- **Hash-mode tables / cipher references** — cracking & crypto.
- Per-engagement notes (scope, prior findings) — a small per-target store the agent reads first.

**Conditional handoffs (examples, not compulsory chains):**
```
Known internal IP -> selected common TCP ports -> a discovered service hypothesis
Known web endpoint -> baseline/page evidence -> one relevant template or manual case
Known AD identity/rights -> one directory or protocol hypothesis -> minimal verified impact
Known artifact -> cheap format/logic triage -> one evidence-led extraction/solve task
```
Skip irrelevant stages. The coordinator chooses after reviewed handback and tracks goal/omissions;
a new identity/unchanged endpoint is not permission to repeat the same scans as fresh evidence.

---

## 8. The `## Checklist` block (verification layer 1)

Every skill carries a `## Checklist` — a fenced YAML block the independent reviewer reads and checks.
It declares each required part *and how to verify it from evidence*. (Example in
`templates/SKILL.template.md`.)

```yaml
checklist:
  - id: scope-confirmed            # stable, unique within the skill; ALWAYS first
    desc: Inherited task scope and applicable endpoints checked
    verify: judge
    evidence: ../../scope.json     # inherited task binding
    on_fail: fail
    required: true
  - id: <step-id>
    desc: What this evidence proves
    verify: nonempty
    evidence: <path relative to the run dir>
    on_fail: redo-part
    required: true
```

**`verify` methods** (reviewer assesses these read-only, without shell execution):

| method | passes when | use for |
|---|---|---|
| `exists` | path exists | bookkeeping only, not proof of execution/impact |
| `nonempty` | exists **and** has content | output that must not be empty |
| `contains:<regex>` | file matches the regex | proof of *real* results (e.g. `open`, `\[critical\]`) |
| `min-lines:<n>` | file has ≥ n lines | required nonempty data only, not legitimate empty discovery |
| `exit-zero` | actual tool exit is 0 and no helper failure | strict clean execution; classified nonzero needs judge |
| `judge` | reviewer reads evidence and assesses vs `desc` | things no pattern captures (scope, triage quality) |

**`on_fail` actions:**

| action | meaning |
|---|---|
| `redo-part` | recommend an exact permitted local documentation/compilation repair to coordinator |
| `redo-skill` | recommend reassessment/new bounded task; never automatic active replay |
| `fail` | fail review; no retry for scope, hard errors, false proof or unsafe/ambiguous actions |

**`required`**: `true` items block a PASS; `false` items are reported but don't fail the review.

**Authoring rules**
- Every item points at actual evidence; command events/native output/real GUI exports prove work,
  not generated findings.md, marker-only narratives or precreated collection/project/loot directories.
  Keep empty native lists/JSON unchanged; separate analysis records scoped negatives/omissions.
- The **scope gate is always `on_fail: fail`** and references inherited `../../scope.json` — never
  retry your way past an unconfirmed target, and never re-confirm scope per run.
- Prefer judge plus real data/paired events for execution/coverage/triage. Positive proof is conditional
  on a positive claim: absent optional proof is not an order to rerun an exploit or collect a flag.
- Keep it to meaningful selected-task items (typically 3–5), with honest partial and no-hit outcomes.

> The run record the helper writes (`run.json`) and its schema, the error-handback
> `findings.md` shape, and the timestamp/self-report/cleanup invariants the reviewer also checks all
> live in **`AGENTS.md`**. This guide does not duplicate them.

---

## 9. The `review` skill & verdicts (verification layer 2)

The `review` skill (`.claude/skills/review/SKILL.md`, category `meta`) is an independent completion
check against the declared bounded profile, not exhaustive coverage. It runs in the exact locked
reviewer context, including standalone invocation; it never starts a helper/shell/nested review run.

**Flow:** load the task skill's `## Checklist` → load `run.json` for context (a parseable `run.json`
is mandatory on any terminal run; missing/unparseable → FAIL) → **re-verify every item independently**
(don't trust `run.json` item `ok`) → check the cross-cutting invariants from `AGENTS.md` (timestamp
sanity, native coverage/outcomes, consistency, provenance, conditional finding proof, cleanup state)
-> decide -> request only permitted coordinator repairs -> write assigned review.json via Write with
an actual coordinator-supplied UTC review time. Initial read budget is 120 seconds.

**Decision logic (summary).** Let `F` = required items that failed.
- Missing/unparseable `run.json`, a guardrail-bypass attempt, or any cross-cutting invariant violation
  → **FAIL** (not retryable).
- `F` empty and invariants hold → **PASS.**
- Any `F` item is `on_fail: fail`, or a hard tool error occurred, -> FAIL. The respected-guardrail
  compliance exception follows AGENTS.md; it is not proof of a completed action or finding.
- Truthful scoped-negative/terminal partial/native-budget and unclaimed missing goal proof do not
  require replay for PASS. Task compliance, coverage and engagement goal are separate judgments.
- A recoverable local documentation/compilation gap is FAILED with an exact coordinator action,
  not PASS based on a recommendation. Actual independently checked repair can be FAILED-RECOVERED.

Reviewers never replay tests/contact targets. Scope/guardrail/transport/actionful/lockout-sensitive
failures are not review-driven retries; missing positives or coverage do not justify broader scanning.

**Verdicts the user sees:**

| Verdict | Meaning | What happens |
|---|---|---|
| `PASS` | Required work or stop compliance independently verified | `review.json` written; do not infer unperformed work |
| `FAILED-RECOVERED` | Actual permitted local recovery independently verified | disclose repair; only proved findings eligible |
| `FAILED` | Required item/invariant unresolved | state exact missing work, cause and permitted coordinator action |
| `NON-COMPLIANT` | Target skill has no `## Checklist` | can't be verified → treated as fail; add a checklist |

Only individually evidence-backed findings with PASS/FAILED-RECOVERED reviews are eligible; terminal
partial can support verified findings but no exhaustive negative. Hard-error/unfinished/unreviewed/
legacy runs stay excluded, and a guardrail compliance PASS is never a finding.

**Worked examples**
- *Bounded ports:* completed top-100 XML and derived empty inventory can PASS for that profile;
  unselected TCP/UDP stay omitted. No fabricated detail file or forced full-port scan.
- *Native FFUF budget:* terminal partial with actual events/native JSON, counts and omitted entries
  can PASS compliance without replay. A default-page/403 match is not a verified vulnerability.
- *Empty Nuclei JSONL:* actual normally ended selected-template events plus triage/coverage can PASS;
  an empty file/marker without events cannot. A hard helper deadline stays error despite flushed output.
- *Collection/logic:* precreated directories without objects/import/query or actual analysis logs
  cannot prove BloodHound/Ghidra work. Honest missing capability remains a goal/coverage limitation.
- *Report repair:* allowed local HTML/markdown mismatch repaired and independently checked can be
  FAILED-RECOVERED; no need or permission to replay a target action.
- *Hard failure (fail fast):* `run.json.status == error`, `errors: ["subfinder: command not found"]`
  → skip all retries → **FAILED**, tell the user to install the tool.

---

## 10. Build order

1. **Finalize the template + schema** (§2–§4) and validate one skill end-to-end (`port-scanner`)
   against the runtime so triggering + `Read` works.
2. **Recon tier-1** (`subfinder`, `httpx`, `port-scanner`, `ffuf`).
3. **Scanning + web-vuln classes** (`nuclei`, then §6: `sqlmap`, `xss`, `ssrf`, `idor`, `burpsuite`).
4. **Access / AD / passwords / privesc** (`exploitation`, `metasploit`, `hydra`, `ssh-foothold`,
   `netexec`, `bloodhound`, `impacket`, `linpeas`, `privesc-root`, `hashcat`).
5. **CTF pwn/RE/forensics** last (highest `effort`, most specialized): `ghidra`, `pwntools`,
   `binwalk`, `steghide`, `wireshark`.
6. **`review`** (meta) and the shared data layer (§7) in parallel from step 2 onward.

Generate **one skill at a time** by cloning a golden reference
(`.claude/skills/port-scanner/SKILL.md` for a deterministic runner,
`.claude/skills/nuclei/SKILL.md` for a triage-heavy one, `.claude/skills/review/SKILL.md` for the
verifier). Do not batch-generate the whole catalog.

---

## Appendix A — optional report examples

These are **optional** patterns for the `reporter` agent, kept here (not hardcoded in
`reporter.md`) so the report structure stays generic. Use them only when the engagement actually fits.

### A.1 Two-phase HTB attack-chain narrative

When an engagement splits cleanly at a privilege boundary (common on HTB/OSCP boxes), the attack-chain
narrative reads well in two phases with any platform guardrail as the pivot. Use events.jsonl UTC
times and per-run seq; merging concurrent runs does not establish causality:

- **Phase 1 — Foothold & user flag:** recon → scan → the exploited vulnerability → initial RCE as the
  service user → user flag.
- **Guardrail interlude (only if one occurred):** privilege-escalation attempts that were **correctly
  stopped by platform safety controls with zero target contact**, and the **user-driven resolution**
  (switch to default/manual permission mode + Cyber Verification Program enrollment) that unblocked the
  work. Record it as a neutral in-place event — what was attempted, that it stopped, how it resolved.
- **Phase 2 — Privilege escalation & root flag:** the successful privesc run (via the identified
  misconfiguration / vector) → root → root flag, **after** the guardrail was resolved.

Missing/legacy timelines are disclosed as unverified; never invent events or derive command times
from folder names. Helper-produced UTC timestamps need no legacy clock workaround.

### A.2 Windows / Active Directory remediation mappings

When a Microsoft/Windows control is the relevant mitigation for a finding, name it explicitly in the
finding's **remediation** field. Common mappings:

| Finding pattern | Remediation control(s) |
|---|---|
| Credential theft / replay (LSASS, tickets) | **Credential Guard**, **Protected Users** group, LSASS protection |
| Local admin password reuse across hosts | **LAPS** (randomized per-host local admin passwords) |
| Service-account Kerberoasting | **gMSA** (managed long random passwords), strong SPN account policy |
| Malware / tooling execution on endpoints | **Microsoft Defender**, **ASR** (Attack Surface Reduction) rules |
| Over-permissioned service accounts | least privilege, tiered admin model, **Protected Users** |

Optionally classify findings with **MITRE ATT&CK** technique IDs and the **PTES** phase in the body —
but **never** as a frontmatter field on a skill.
