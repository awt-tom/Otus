---
name: <tool>                      # lowercase/kebab-case, equals the folder name
description: >                    # TRIGGER TEXT — "Use when <task>, with <tool + aliases>." Keyword-dense.
  One or two sentences written so the matcher fires on the right requests and nothing else.
  Say when NOT to use it (name the sibling skill to prefer instead).
arguments: "<positional args>"   # required first, optional in [brackets]; keep to <= 3-4
model: inherit                    # always 'inherit' — use the session model; never hardcode sonnet/opus/haiku
effort: low | medium | high       # by weight — see docs/authoring.md "Model / effort convention"
context: fork                     # direct invocation forks into the canonical owner
agent: <owner>                    # exact role from AGENTS.md; never a generic substitute
background: false                # await terminal handback before dependent work
category: recon | web | access | ad-network | privesc-creds | re-forensics | meta
domain: web | ad | network | host | crypto | binary | forensics | misc
---

# <tool> — <one-line what-it-does>

Shared contract: see AGENTS.md.

## Goal (desired outcome)
What this selected bounded task proves, for which goal, and what it cannot establish. 1-2 sentences.

## Steps
1. Select the cheapest discriminating test from checked inputs. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill <tool> --profile "$PROFILE" --coverage-set "$COVERAGE")"`.
  `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Use `--targets-file "$HOSTS"` for batches; offline work omits target options.
2. Write notes/task.md with hypothesis, version/inputs, profile, finite total/command budget, useful-progress criterion, escalation trigger and stop conditions. Verify identity/help before contact; choose a native budget below the helper cap where supported.
3. `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --timeout 60 --grace 5 -- <exact verified bounded argv>`; replace 60 with the justified finite cap. Offline work omits target options; GUI work saves real exports and `event --event marker`, not invented commands.
4. Inspect actual native coverage/health, then minimal verification/triage. A larger/deeper test needs a specific lead and remaining allocation, never an empty-result ladder. Preserve native empty files unchanged; notes/assessment.md describes scoped negative, partial or error and evidence refs.
5. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --stop-reason "$STOP" --omitted "$OMITTED" --item 'scope-confirmed=ok:../../scope.json'`; add supported items/findings and actual state/cleanup. Update profile/set if a justified branch changed it; --observed only from native accounting. Return next-task proposal to coordinator, no worker chain. Review uses its locked verdict-writing exception, not this executable lifecycle.

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
  # --- tool-unique items: selected execution, actual coverage and conditional proof ---
  - id: <step-id>
    desc: What events and native artifacts independently prove for the declared profile
    verify: judge        # existence/markers alone do not prove execution or impact
    evidence: <actual event/native/analysis path relative to the run dir>
    on_fail: fail        # redo-part/redo-skill recommend permitted coordinator repairs, not active replay
    required: true
```

## Notes / pitfalls
Tool-specific gotchas only — rate limits, false positives, destructive flags to avoid by default,
auth handling, and which raw evidence to save to `loot/` for the reviewer. Do **not** restate the
shared contract; link to AGENTS.md if a rule needs emphasis.
