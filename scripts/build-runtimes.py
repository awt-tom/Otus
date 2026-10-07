#!/usr/bin/env python3
"""Regenerate the runtime-specific instruction files from AGENTS.md.

AGENTS.md is the single source of truth for the Otus agent contract. This script
reads it and writes the generated adapters:

  * CLAUDE.md                        = contract + a Claude Code agent-routing appendix
  * .github/copilot-instructions.md  = contract + a short GitHub Copilot note
  * .github/agents/otus.agent.md     = YAML-first Copilot coordinator

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

Discover the flat `.claude/skills/` and four `.claude/agents/` definitions using the installed
runtime's supported discovery. Follow the canonical ownership table above; the parent uses actual
Agent calls with exact role names, one selected skill/profile per worker. Direct skill forks select
the same owner. A spawned worker Read/executes its runbook without invoking Skill/Agent again.
Await terminal handback, independently review it with a coordinator-supplied actual UTC timestamp,
then choose the next evidence-triggered task. Report through the reporter and review that output.
For example, an internal IP can start with a bounded common-port scan, then a discovered web service;
it does not require public subdomain discovery or every scanner. Never silently substitute a generic
agent when a registered role/required permission is missing. Validate discovery and tool enforcement
offline before target work; see docs/authoring.md for runtime setup and acceptance checks.
"""

COPILOT_APPENDIX = """## GitHub Copilot runtime

GitHub Copilot auto-includes this file in every chat/agent session for this repo. The contract above
is authoritative; the per-tool runbooks live under `.claude/skills/<tool>/SKILL.md` and the authoring
spec in `docs/authoring.md`.

- Supported VS Code runtimes discover `.claude/skills/` and native `.claude/agents/*.md`.
  Verify installed-version support and discovery diagnostics; do not assume unknown config keys.
- Select the generated `.github/agents/otus.agent.md` coordinator, or use built-in Agent with
  the same canonical named delegation. The parent must have the agent tool and invoke the exact
  recon-runner, vuln-hunter, reviewer and reporter roles; no handoff-button or generic-agent substitute.
  Workers Read/execute only the assigned runbook without nested forks. Await actual handbacks.
- Agent/tool metadata is runtime-dependent. Check resolved permissions: reviewer has no execution;
  reporter cannot assemble with broad execute. Fail setup closed instead of widening capabilities.
- When writing or editing a skill, follow `docs/authoring.md` and `templates/SKILL.template.md`
  exactly: keep skills flat at `.claude/skills/<tool>/SKILL.md`, never invent tool flags, and never
  restate this contract in a skill body — reference it with the single line
  `Shared contract: see AGENTS.md`.
- Skills call `scripts/otus-log.py` for scope checks, raw logs, events, and rendered findings.
  Evidence uses `$OTUS_HOME` or `<repo>/out`; review/report direct-writing exceptions are above.
- Don't commit engagement evidence (including custom `$OTUS_HOME` roots), or real credentials or scope
  notes to tracked files.
"""

TARGETS = {
    ROOT / "CLAUDE.md": CLAUDE_APPENDIX,
    ROOT / ".github" / "copilot-instructions.md": COPILOT_APPENDIX,
}

COORDINATOR_HEADER = """---
name: otus
description: Coordinate goal-driven authorized Otus tasks with bounded named workers and independent review.
tools: [read, search, edit, execute, agent, todo]
agents: [recon-runner, vuln-hunter, reviewer, reporter]
user-invocable: true
disable-model-invocation: true
---
"""

COORDINATOR_BODY = """# Otus Coordinator

Read ../../AGENTS.md before engagement work. Its ownership table, scope, allocation, progress,
health, review and permission gates are authoritative; do not replace them with a fixed tool chain.
Read docs/authoring.md for installed-runtime discovery and offline startup acceptance.

Use the agent tool to call the exact registered owner with one concrete skill/profile and complete
task inputs. Give reviewer the actual UTC review timestamp and exact terminal run directory.
Await the real result and inspect the verdict artifact before dependent work. Maintain private
engagement notes/progress.md yourself; workers propose updates. Reporter compilation is followed
by independent report review. Workers must not invoke child agents or fork skills again.

For an explicit offline read-only setup check, invoke each named role with no targets, commands,
evidence writes or invented authorization. Return actual startup/capability limitations. Missing
roles or unenforceable locked permissions stop setup, not a request for a generic replacement.
"""

AGENT_TARGETS = {ROOT / ".github" / "agents" / "otus.agent.md": COORDINATOR_BODY}


def render(contract: str, appendix: str) -> str:
    return f"{GENERATED_HEADER}\n{contract.rstrip()}\n\n---\n\n{appendix.rstrip()}\n"


def render_agent(body: str) -> str:
    return f"{COORDINATOR_HEADER}\n{GENERATED_HEADER}\n{body.rstrip()}\n"


def main() -> int:
    if not AGENTS.exists():
        print(f"error: {AGENTS} not found", file=sys.stderr)
        return 1
    contract = AGENTS.read_text(encoding="utf-8")
    for path, appendix in TARGETS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(contract, appendix), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    for path, body in AGENT_TARGETS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_agent(body), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
