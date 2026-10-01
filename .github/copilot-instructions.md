# Otus — Copilot instructions

> Auto-included by GitHub Copilot in every chat/agent session for this repo. Keep it short; the depth lives in `docs/`.

## What this repo is
Otus is a library of **offensive-security skills** for an LLM agent. Each skill is a folder with a `SKILL.md` runbook the agent loads on demand. Authoritative specs:
- `docs/kali-bugbounty-ctf-skills-reference.md` — skill format, metadata schema, body template (§3), model/effort/context/agent guidance (§4), tool catalog (§5), repo layout + tool→capability map (§8), build order (§9).
- `docs/skill-verification-and-review.md` — the `## Checklist` spec (§2), the `_run.json` run record (§3), and the Reviewer skill (§4).

**When writing or editing any skill, read those two docs first and follow them exactly.**

## Hard rules
1. **Scope / authorization.** These skills run real offensive tools. They are for authorized work only (in-scope bug-bounty programs, CTF/HTB labs, owned systems). Every `SKILL.md` body starts with the scope-guard line from the template. Never remove it.
2. **Never invent tool flags or commands.** Use the exact command forms in the reference's catalog entry for that tool. If a flag isn't in the reference, verify it against the tool's `--help` or official docs before writing it. A wrong flag is worse than an omission.
3. **Folder & file convention.** One **PascalCase capability** folder per skill, flat under `skills/`: `skills/<CapabilityName>/SKILL.md`. The file is `SKILL.md` (uppercase). `name:` in frontmatter equals the folder name. See the tool→capability map in reference §8.
4. **Use the template verbatim.** Every `SKILL.md` has the frontmatter schema (reference §2) and the body sections in order: Goal, Steps, Modern tooling & alternatives, Output formats, RAG / shared data / cross-skill, **Checklist**, Notes / pitfalls.
5. **Checklist is mandatory.** Fill the `## Checklist` (fenced ```yaml) per §2 of the verification doc. The scope-gate item is always `on_fail: fail`. Any step that can legitimately produce nothing must still write a marker file so "ran but empty" ≠ "didn't run".
6. **Run record.** Skill bodies write evidence + `_run.json` to `out/<CapabilityName>/`. `out/` is git-ignored.
7. **One skill at a time.** Generate each new skill by cloning the style of an existing golden skill, e.g.: *"generate `skills/ContentDiscovery/SKILL.md` in the exact style of `#file:skills/PortScanner/SKILL.md`, using the catalog entry for ffuf in `#file:docs/kali-bugbounty-ctf-skills-reference.md`."* Do not batch-generate the whole catalog.

## Golden references to copy from
- `skills/PortScanner/SKILL.md` — deterministic runner example (nmap).
- `skills/VulnScanner/SKILL.md` — triage-heavy example (nuclei).
- `skills/Reviewer/SKILL.md` — the verification skill (build from verification doc §4).

## Build order
Follow reference §9: `SubdomainRecon` → `HttpProbe` → `PortScanner` → `ContentDiscovery` → `VulnScanner` → web-vuln classes (§6) → exploitation / AD / passwords / privesc → CTF pwn/RE/forensics last.

## Vuln-category skills
For a vulnerability class (not a tool), make one narrow skill per class (`SqlInjection`, `XSS`, `SSRF`, `IDOR`, …). The body is a testing methodology that names which tool skills to invoke. See reference §6.

## Out of scope for Copilot here
Don't write exploit payloads against targets, don't add real credentials or scope notes to tracked files, and don't commit anything under `out/`.