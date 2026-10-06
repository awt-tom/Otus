#!/usr/bin/env python3
"""Regenerate the runtime-specific instruction files from AGENTS.md.

AGENTS.md is the single source of truth for the Otus agent contract. This script
reads it and writes two generated adapters:

  * CLAUDE.md                        = contract + a Claude Code agent-routing appendix
  * .github/copilot-instructions.md  = contract + a short GitHub Copilot note

Stdlib only, no network. Run from anywhere:

    python3 -I scripts/build-runtimes.py
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"

GENERATED_HEADER = (
    "<!-- GENERATED from AGENTS.md — do not edit directly.\n"
    "     Edit AGENTS.md, then run: python3 -I scripts/build-runtimes.py -->\n"
)

CLAUDE_APPENDIX = """## Claude Code runtime — agent routing

Claude Code and OpenCode read `.claude/skills/` natively (flat, one tool-named folder per skill).
`.claude/agents/` adds four subagents that run those skills in isolated contexts:

- **Recon / enumeration** (subfinder, httpx, port-scanner, ffuf) → `recon-runner`.
- **Scanning / exploitation / post-exploitation** (nuclei, the web-vuln classes, `exploitation`,
  `ssh-foothold`, `metasploit`, `linpeas`, `privesc-root`, `netexec`, `bloodhound`, `impacket`,
  `hashcat`, `hydra`) → `vuln-hunter`.
- **After every skill run**, hand the run dir to `reviewer` (which reads the `review` skill) before
  results are treated as final.
- **At the end of an engagement** (or on request to write/summarize the report) → `reporter`. It
  reads across `out/`, writes only under `out/<engagement>/report/`, produces markdown plus a
  branded self-contained HTML, and never contacts targets.

A typical chain: `subfinder` → `httpx` → `port-scanner` + `ffuf` → `nuclei` → web-vuln classes →
`exploitation` / `privesc-root`, with `review` after each stage and `reporter` at the end. This is
the Claude Code wiring of the runtime-agnostic "Engagement workflow" section above.
"""

COPILOT_APPENDIX = """## GitHub Copilot runtime

GitHub Copilot auto-includes this file in every chat/agent session for this repo. The contract above
is authoritative; the per-tool runbooks live under `.claude/skills/<tool>/SKILL.md` and the authoring
spec in `docs/authoring.md`.

- Point Copilot's `skillDirectories` config at `./.claude/skills` so it can load the skills (flat,
  one tool-named folder per skill — verify the key name in your Copilot setup).
- When writing or editing a skill, follow `docs/authoring.md` and `templates/SKILL.template.md`
  exactly: keep skills flat at `.claude/skills/<tool>/SKILL.md`, never invent tool flags, and never
  restate this contract in a skill body — reference it with the single line
  `Shared contract: see AGENTS.md`.
- Don't commit anything under `out/` (git-ignored evidence), and never add real credentials or scope
  notes to tracked files.
"""

TARGETS = {
    ROOT / "CLAUDE.md": CLAUDE_APPENDIX,
    ROOT / ".github" / "copilot-instructions.md": COPILOT_APPENDIX,
}


def render(contract: str, appendix: str) -> str:
    return f"{GENERATED_HEADER}\n{contract.rstrip()}\n\n---\n\n{appendix.rstrip()}\n"


def main() -> int:
    if not AGENTS.exists():
        print(f"error: {AGENTS} not found", file=sys.stderr)
        return 1
    contract = AGENTS.read_text(encoding="utf-8")
    for path, appendix in TARGETS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(contract, appendix), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
