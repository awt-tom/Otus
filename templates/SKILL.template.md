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
1. Set inputs from the user. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill <tool>)"`.
  `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Use `--targets-file "$HOSTS"` for batches; offline work omits target options.
2. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" -- <exact original executable argv>`; all active commands use this wrapper, including verification. Offline work omits target options; GUI work saves exports and records `event --event marker` instead.
3. Decision point: if X then …, else …
4. Verify / triage the results (drop false positives; keep only real findings).
5. Preserve raw outputs and empty-result markers; name the next skill. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json'`; add actual checklist items, verified `--finding` entries, and target-state/cleanup fields. Error paths and rendered findings follow AGENTS.md; never hand-write JSON or findings.md.

## Modern tooling & alternatives
Current best-in-class, notable flags, and the legacy tools this replaces. Note version-sensitive
behaviour.

## Checklist
```yaml
checklist:
  - id: scope-confirmed            # always first; references the inherited engagement scope
    desc: Explicit engagement authorization and applicable endpoints checked
    verify: judge
    evidence: ../../scope.json
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
