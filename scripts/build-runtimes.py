#!/usr/bin/env python3
"""Regenerate the runtime-specific instruction files from AGENTS.md.

AGENTS.md is the single source of truth for the Otus agent contract. This script
reads it and writes the generated adapters:

  * CLAUDE.md                        = contract + a Claude Code agent-routing appendix
  * .github/copilot-instructions.md  = contract + a short GitHub Copilot note
  * .github/agents/otus.agent.md     = YAML-first Copilot coordinator
  * .opencode/agents/*.md           = generated OpenCode v2 role adapters
  * .opencode/opencode.json         = provider-independent default coordinator

Stdlib only, no network. Run from anywhere:

    python3 -I scripts/build-runtimes.py
"""

import argparse
import json
import pathlib
import re
import runpy
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
Initialize the parent-bound task scope as AGENTS.md directs before active delegation. Inherit the
same engagement/evidence root and checked targets through every worker; authorizer metadata is
not a prerequisite. Resume the persisted engagement context rather than silently making a new one.

Use the agent tool to call the exact registered owner with one concrete skill/profile and complete
task inputs. Give reviewer the actual UTC review timestamp and exact terminal run directory.
Await the real result and inspect the verdict artifact before dependent work. Maintain private
engagement notes/progress.md yourself; workers propose updates. Reporter compilation is followed
by independent report review. Workers must not invoke child agents or fork skills again.

For an explicit offline read-only setup check, invoke each named role with no targets, commands,
evidence writes or invented engagement records. Return actual startup/capability limitations. Missing
roles or unenforceable locked permissions stop setup, not a request for a generic replacement.
"""

AGENT_TARGETS = {ROOT / ".github" / "agents" / "otus.agent.md": COORDINATOR_BODY}

WORKERS = ("recon-runner", "vuln-hunter", "reviewer", "reporter")
CATALOG = runpy.run_path(str(ROOT / "scripts" / "build-catalog.py"))
OPENCODE_CONFIG = {"default_agent": "otus"}
OPENCODE_PREAMBLE = """## OpenCode V2 Compatibility

Read AGENTS.md from the repository root. Resolve inherited repository paths there; the
coordinator's source-relative ../../AGENTS.md refers to that same contract.
Claude Read/Write/Grep/Glob/Bash names in the inherited procedure mean OpenCode read,
write/edit/patch, grep, glob and shell, subject to this role's actual permissions.

When this role permits commands, use the shell tool directly for OS commands, CLI tools,
scripts and security tooling. execute is JavaScript Code Mode, NOT a shell; it is disabled
for Otus roles. Never put shell syntax into execute or substitute another execution tool.
Use the repository-root workdir and foreground shell calls, non-interactive flags and closed
stdin. Keep the existing otus-log.py wrapper, target checks and finite helper timeout/grace.
Shell timeout is milliseconds: set it to at least (helper timeout + grace + 30) * 1000;
the default two-minute shell timeout is not a sufficient outer bound for longer helper jobs.
Shell calls are fresh: retain absolute run paths and pass required environment explicitly,
not an assumed RUN variable from a previous call. A locked role must not execute commands.

Skills are the original .claude/skills/<name>/SKILL.md files, discovered natively by v2.
Loading a skill does not honor Claude context:fork or agent metadata. The parent selects
the canonical owner and uses the foreground subagent tool with complete inherited inputs.
Workers read ONLY the selected runbook in their existing context; no nested skill/agent forks.
Missing named roles or unenforceable restrictions fail setup; never fall back to Explore/general.
Await terminal handbacks and real verdict files before dependent work or reporting.

Before finishing, every item marked ok must have its evidence file present and nonempty; otherwise
mark it fail with the reason. Never mark an item ok, or drop a required item, to satisfy a verdict.
A FAILED review gets one bounded repair from real native output in the same run; if it still fails,
finish partial or error and hand the unresolved verdict to the user. Do not re-run the same worker
in a loop, and do not start new active work to clear a review.

External OTUS_HOME roots need existing user-approved path permissions. Generated path
allowlists are not a filesystem sandbox or proof of assigned-path enforcement. Verify actual
merged permissions, reviewer no-shell and reporter restricted-shell behavior before work;
never widen global permissions or bypass runtime policies/refusals to make an adapter work.
"""


def role_source(name: str) -> tuple[str, str, str]:
  path = ROOT / ".claude" / "agents" / f"{name}.md"
  text = path.read_text(encoding="utf-8")
  frontmatter = CATALOG["_frontmatter"](text)
  metadata = CATALOG["parse_skill"](path)
  if not frontmatter or metadata["name"] != name or not metadata["description"]:
    raise ValueError(f"invalid canonical agent metadata: {path}")
  body = "".join(text.splitlines(keepends=True)[len(frontmatter.splitlines()) + 2:]).lstrip("\n")
  return metadata["description"], frontmatter, body


def opencode_permissions(name: str, frontmatter: str = "") -> list[dict[str, str]]:
  rules = [{"action": "*", "resource": "*", "effect": "deny"}]
  if name == "otus":
    tools = ("Read", "Write", "Grep", "Glob", "Bash")
  else:
    match = re.search(r"^tools:\s*(.+)$", frontmatter, re.MULTILINE)
    if not match:
      raise ValueError(f"missing canonical tools for {name}")
    tools = tuple(tool.strip() for tool in match.group(1).split(","))
  actions = {"Read": "read", "Write": "edit", "Grep": "grep", "Glob": "glob", "Bash": "shell"}
  for tool in tools:
    if tool in actions:
      resource = "*"
      if tool == "Write":
        resource = {"reviewer": "out/*/*/*/review.json", "reporter": "out/*/report/*"}.get(name, "out/*")
      rules.append({"action": actions[tool], "resource": resource, "effect": "allow"})
    else:
      match = re.fullmatch(r"Bash\(([^)]+)\)", tool)
      if not match:
        raise ValueError(f"unsupported canonical tool for {name}: {tool}")
      rules.append({"action": "shell", "resource": match.group(1), "effect": "allow"})
  if name == "otus":
    rules.extend({"action": "subagent", "resource": worker, "effect": "allow"} for worker in WORKERS)
    rules.extend({"action": action, "resource": "*", "effect": "allow"} for action in ("skill", "question"))
  rules.extend([
    {"action": "external_directory", "resource": "*", "effect": "ask"},
    {"action": "read", "resource": "*.env", "effect": "ask"},
    {"action": "read", "resource": "*.env.*", "effect": "ask"},
    {"action": "read", "resource": "*.env.example", "effect": "allow"},
    {"action": "execute", "resource": "*", "effect": "deny"},
  ])
  return rules


def render_opencode_agent(name: str) -> str:
  if name == "otus":
    description = "Coordinate bounded Otus tasks with named workers and independent review."
    frontmatter, body = "", COORDINATOR_BODY
    source = "AGENTS.md and scripts/build-runtimes.py"
  else:
    description, frontmatter, body = role_source(name)
    source = f"AGENTS.md and .claude/agents/{name}.md"
  lines = ["---", "description: " + json.dumps(description),
       "mode: " + ("primary" if name == "otus" else "subagent"), "permissions:"]
  lines.extend("  - " + json.dumps(rule) for rule in opencode_permissions(name, frontmatter))
  lines.extend(["---", "", f"<!-- GENERATED from {source}; do not edit directly.",
          "     Regenerate with: python3 -I scripts/build-runtimes.py -->", "",
          OPENCODE_PREAMBLE.rstrip(), "", body.rstrip(), ""])
  return "\n".join(lines)


def opencode_outputs() -> dict[pathlib.Path, str]:
  outputs = {ROOT / ".opencode" / "agents" / f"{name}.md": render_opencode_agent(name)
         for name in ("otus", *WORKERS)}
  outputs[ROOT / ".opencode" / "opencode.json"] = json.dumps(OPENCODE_CONFIG, indent=2) + "\n"
  return outputs


def render(contract: str, appendix: str) -> str:
    return f"{GENERATED_HEADER}\n{contract.rstrip()}\n\n---\n\n{appendix.rstrip()}\n"


def render_agent(body: str) -> str:
    return f"{COORDINATOR_HEADER}\n{GENERATED_HEADER}\n{body.rstrip()}\n"


def main() -> int:
    if not AGENTS.exists():
        print(f"error: {AGENTS} not found", file=sys.stderr)
        return 1
    try:
      opencode = opencode_outputs()
    except (OSError, ValueError) as error:
      print(f"error: {error}", file=sys.stderr)
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
    for path, content in opencode.items():
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(content, encoding="utf-8")
      print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    argparse.ArgumentParser(
        description="Regenerate runtime adapter files from AGENTS.md. Takes no options."
    ).parse_args()
    raise SystemExit(main())
