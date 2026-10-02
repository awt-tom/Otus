# Otus runtime routing
- Recon tasks (subfinder, httpx, port-scanner, ffuf) → delegate to the `recon-runner` subagent.
- Scanning/exploitation (nuclei, web-vuln classes, exploitation) → delegate to the `vuln-hunter` subagent.
- After every skill run, hand the run dir to the `reviewer` subagent (which reads the `review` skill) before results are final.
- All work is lab/authorized only. Agents must confirm scope before any active step.

## Target host resolution (all skills)
- If a target vhost does not resolve, add it to `/etc/hosts` **only when sudo is available non-interactively** (`sudo -n true` succeeds): `echo "<ip> <vhost>" | sudo -n tee -a /etc/hosts`.
- Otherwise do **not** force sudo — standardise on the tool's own resolution override: `--resolve <host>:<port>:<ip>` (curl/ffuf) or an HTTP `Host: <vhost>` header (nuclei/curl `-H`).
- Whichever path is used, log it to `notes/dns-workaround.txt` in the run dir so it is auditable.
- Never run interactive sudo or prompt for a password to edit `/etc/hosts`.

## Platform guardrail handling (hard — never bypass)
A **platform guardrail** is a refusal from the runtime itself (not a scope error or a missing tool):
- a Claude Code auto / accept-edits permission-mode **safety classifier** refusal ("Claude could not evaluate this action" / "could not evaluate this action"), or
- an Anthropic **API cyber safeguard** (`invalid_request`, or an error `detail` tagged `[cyber]`).

When a tool call is refused by **either**, the executor MUST immediately:
1. **Stop all further active steps** for that run — do not run the next step.
2. Write `_run.json` with `status: "error"` and an `errors[]` entry recording the **block type** (`guardrail:permission-classifier` or `guardrail:api-cyber-safeguard`) and the **request id** if one is present.
3. Write `summary.txt` in the error-handback shape (docs/skill-review-guide.md §3).
4. **Hand back to the user** and stop.

It MUST NOT retry the same or a reworded/re-encoded command, split the command into smaller pieces, move it to background/detached execution, switch tools to achieve the same effect, or attempt any other bypass. **Respecting the block is the correct outcome, not a routing failure.** Resolution is **user-driven only**: the user may switch Claude Code to manual/default permission mode (and approve the action themselves) and/or enroll in Anthropic's Cyber Verification Program. Agents never make that change on the user's behalf.

## Self-report consistency (hard)
`_run.json` narrative/notes fields and `summary.txt` must never state anything that contradicts the on-disk evidence or `notes/*.txt` (e.g. do not claim `--resolve` was used when a `Host:` header was used). Describe the method **exactly as performed**; when unsure, state what was actually done. The reviewer treats any run↔evidence contradiction as a failure.

## Run-dir isolation (parallel subagents)
Each skill/subagent writes **only** into its own run dir. The orchestrator may pin a dir by exporting `OTUS_RUN_DIR` before invoking a skill; otherwise the skill mints a unique dir `out/<skill>/<UTC-timestamp>-<pid>` and stores it in a uniquely-named variable `OTUS_RUN_<skill>` — never a bare shared `$RUN` that a concurrently-running sibling could overwrite. When routing work to **parallel** `recon-runner` / `vuln-hunter` subagents, give each its own run dir (distinct `OTUS_RUN_DIR`, or let each mint its own) so concurrent runs can't clobber each other's `out/` dirs.

## Run-record invariant (hard)
`_run.json` MUST be written on **every** terminal outcome — success, partial, or error — **before handback**, by every skill and every agent. A run that produced evidence but no parseable `_run.json` is itself a defect; the reviewer FAILS it.

## Cleanup-state verification (hard)
A run may declare "no cleanup needed" ONLY if it made no state-changing actions. If it created **any** artifact on the target (injected DB rows, planted files, created users/cron entries, dropped implants), it must verify removal with **positive evidence** before declaring clean: re-query / re-list that exact artifact and show it **absent**, saved to `loot/cleanup_verify.txt` (e.g. a credentialed re-count of `0`, a directory listing without the planted file). For error/aborted runs, the error-handback `summary.txt` cleanup-state field must record what was created before the stop and whether it was removed or is **STILL OWED**. Never accept an unverified "clean" claim.
