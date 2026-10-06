---
name: <tool>                      # lowercase/kebab-case, equals the folder name
description: >                    # TRIGGER TEXT — "Use when <task>, with <tool + aliases>." Keyword-dense.
  One or two sentences written so the matcher fires on the right requests and nothing else.
  Say when NOT to use it (name the sibling skill to prefer instead).
arguments: "<positional args>"   # required first, optional in [brackets]; keep to <= 3-4
model: inherit                    # always 'inherit' — use the session model; never hardcode sonnet/opus/haiku
effort: low | medium | high       # by weight — see docs/authoring.md "Model / effort convention"
context: inline | fork            # 'fork' runs the body in a forked subagent
agent:                            # only when context: fork (e.g. Explore, general-purpose)
category: recon | web | access | ad-network | privesc-creds | re-forensics | meta
domain: web | ad | network | host | crypto | binary | forensics | misc
---

# <tool> — <one-line what-it-does>

Shared contract: see AGENTS.md.

## Goal (desired outcome)
What a successful run produces and why you'd reach for this. 1-2 sentences.

## Steps
1. Inputs / precondition. Set up the run dir per AGENTS.md (`$RUN`); scope is already confirmed once
   in `out/<engagement>/scope.txt`, so do not re-confirm it here.
2. `<exact command form — copy the tool's real flags verbatim; never invent a flag>`
3. Decision point: if X then …, else …
4. Verify / triage the results (drop false positives; keep only real findings).
5. Hand-off: write outputs to `$RUN/` and name the next skill to chain. A step that can legitimately
   find nothing still writes a marker file so "ran but empty" ≠ "didn't run". Then write `run.json`.

## Modern tooling & alternatives
Current best-in-class, notable flags, and the legacy tools this replaces. Note version-sensitive
behaviour.

## Checklist
```yaml
checklist:
  - id: scope-confirmed            # always first; references the inherited engagement scope
    desc: Engagement scope confirmed once in out/<engagement>/scope.txt (inherited, not re-confirmed)
    verify: judge
    evidence: ../../scope.txt
    on_fail: fail
    required: true
  # --- tool-unique items below: 3-6 that prove THIS tool actually ran and produced real results ---
  - id: <step-id>
    desc: What this evidence proves
    verify: nonempty      # one of: exists | nonempty | contains:<regex> | min-lines:<n> | exit-zero | judge
    evidence: <path relative to the run dir>
    on_fail: redo-part    # one of: redo-part | redo-skill | fail
    required: true
```

## Notes / pitfalls
Tool-specific gotchas only — rate limits, false positives, destructive flags to avoid by default,
auth handling, and which raw evidence to save to `loot/` for the reviewer. Do **not** restate the
shared contract; link to AGENTS.md if a rule needs emphasis.
