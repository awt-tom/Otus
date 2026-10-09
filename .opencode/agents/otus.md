---
description: "Coordinate bounded Otus tasks with named workers and independent review."
mode: primary
permissions:
  - {"action": "*", "resource": "*", "effect": "deny"}
  - {"action": "read", "resource": "*", "effect": "allow"}
  - {"action": "edit", "resource": "out/*", "effect": "allow"}
  - {"action": "grep", "resource": "*", "effect": "allow"}
  - {"action": "glob", "resource": "*", "effect": "allow"}
  - {"action": "shell", "resource": "*", "effect": "allow"}
  - {"action": "subagent", "resource": "recon-runner", "effect": "allow"}
  - {"action": "subagent", "resource": "vuln-hunter", "effect": "allow"}
  - {"action": "subagent", "resource": "reviewer", "effect": "allow"}
  - {"action": "subagent", "resource": "reporter", "effect": "allow"}
  - {"action": "skill", "resource": "*", "effect": "allow"}
  - {"action": "question", "resource": "*", "effect": "allow"}
  - {"action": "external_directory", "resource": "*", "effect": "ask"}
  - {"action": "read", "resource": "*.env", "effect": "ask"}
  - {"action": "read", "resource": "*.env.*", "effect": "ask"}
  - {"action": "read", "resource": "*.env.example", "effect": "allow"}
  - {"action": "execute", "resource": "*", "effect": "deny"}
---

<!-- GENERATED from AGENTS.md and scripts/build-runtimes.py; do not edit directly.
     Regenerate with: python3 -I scripts/build-runtimes.py -->

## OpenCode V2 Compatibility

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

# Otus Coordinator

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
