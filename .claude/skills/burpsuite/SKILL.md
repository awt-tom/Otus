---
name: burpsuite
description: >
  Use when manually testing a web application with Burp Suite — intercepting proxy, mapping
  the app, Repeater-driven exploitation, Intruder fuzzing, and authz/logic testing. A GUI
  methodology (set scope → proxy/map → Repeater → Intruder → export), the manual hub that
  feeds sqlmap and the vuln-category skills. Not for automated template scanning (use nuclei)
  or pure content discovery (use ffuf).
arguments: "target_or_urls [extension]"
model: inherit
effort: high
context: inline
agent:
---

# burpsuite — intercepting proxy & manual web-testing methodology

**Scope guard:** Authorized targets only (in-scope program / lab / owned). Set Burp's **Target → Scope** to in-scope hosts only and enable "and URLs in target scope" proxy/logging filters *before* touching the app, so you never proxy, crawl, or attack out-of-scope traffic. Abort if the target is not confirmed in scope.

## Goal (desired outcome)
Manually intercept, inspect, modify, and replay HTTP(S) against an in-scope web app — mapping the
attack surface and driving Repeater/Intruder exploitation (IDOR/authz/logic, injection leads) — with
evidence captured deliberately, since most of the work is manual and not reproduced by a single command.

## Steps
1. **Precondition / scope / inputs.** Confirm the target is in scope. In Burp set **Target → Scope**
   to in-scope hosts only and restrict Proxy/Logger to in-scope URLs so nothing out-of-scope is
   captured or attacked. Anchor a timestamped run directory to the repo root (never write under
   `skills/`) for exported artifacts:
   ```bash
   ROOT="$(git rev-parse --show-toplevel)"
   OTUS_RUN_burpsuite="${OTUS_RUN_DIR:-$ROOT/out/burpsuite/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
   RUN="$OTUS_RUN_burpsuite"
   mkdir -p "$RUN/notes" "$RUN/requests"
   echo "target confirmed in scope + Burp scope restricted: <who/when/program-or-lab>" > "$RUN/notes/scope.txt"
   : > "$RUN/run.log"; : > "$RUN/notes/sitemap.md"; : > "$RUN/findings.md"
   ```
2. **Proxy + map the app.** Route the browser through Burp, authenticate, and browse/crawl the
   in-scope app so the **Target → Site map** populates. Capture the mapped endpoints/parameters
   into `notes/sitemap.md` (export selected sitemap items or paste the host tree) so "mapped" is
   evidenced, not assumed.
3. **Repeater — targeted testing.** Send interesting requests to **Repeater**; test IDOR / broken
   authz / business logic by swapping IDs, tokens, and roles, and tampering parameters. Save the
   raw request/response of anything notable into `requests/` (one file per case). Hand injectable
   parameters to `sqlmap` (save item → `req.txt`) rather than brute-forcing injection here.
4. **Intruder + helper tools.** Use **Intruder** for targeted fuzzing (payload positions, sniper/
   cluster-bomb), and **Decoder / Comparer / Sequencer** as needed. Extensions worth loading:
   **Autorize** (authz), **Param Miner** (hidden params), **Logger++**. Pass the requested
   `extension`, if any, in `notes/`.
5. **Record findings + marker.** Write each finding (endpoint, request, observation, impact) to
   `findings.md`, then always write a run marker so "ran but empty" ≠ "didn't run":
   ```bash
   if grep -qiE '^\- ' "$RUN/findings.md"; then echo "burpsuite: findings recorded" > "$RUN/summary.txt";
   else echo "no findings recorded" > "$RUN/summary.txt"; fi
   ```
   Then write the run record `_run.json` into `$RUN/` (schema in Output formats).

## Modern tooling & alternatives
Burp Suite is the standard — **Pro** for active scan/extensions, **Community** for manual Repeater/
Intruder (throttled). `Caido` is a fast-growing lighter alternative; OWASP `ZAP` is the open-source
option. For automated known-pattern scanning use `nuclei`; for content discovery use `ffuf` — Burp
is the manual hub that ties their output together.

## Output formats
GUI tool — evidence is captured deliberately: Burp **project file** and exported **report (HTML/XML)**
plus copied raw requests. This skill writes `$RUN/notes/sitemap.md` (mapped surface),
`$RUN/requests/*` (saved request/response cases), `$RUN/findings.md`, `$RUN/summary.txt` (run marker),
`$RUN/run.log`, and a run record `$RUN/_run.json`:
```json
{
  "skill": "burpsuite",
  "target": "<target_or_urls>",
  "run_dir": "out/burpsuite/<timestamp>",
  "started": "<ISO8601>",
  "finished": "<ISO8601>",
  "status": "complete",
  "items": {
    "scope-confirmed":   { "attempted": true, "ok": true, "evidence": "notes/scope.txt" },
    "app-mapped":        { "attempted": true, "ok": true, "evidence": "notes/sitemap.md" },
    "requests-tested":   { "attempted": true, "ok": true, "evidence": "summary.txt" },
    "evidence-exported": { "attempted": true, "ok": true, "evidence": "requests" }
  },
  "errors": []
}
```
`status` ∈ `complete | partial | error`. On a hard failure (target unreachable, out of scope, Burp
unavailable) set `status: error` and push a human-readable line to `errors[]`.

## RAG / shared data / cross-skill
Central hub — receives endpoints from `katana` / `ffuf` / `httpx`, hands injectable requests to
`sqlmap`, and surfaces leads for the vuln-category skills (`idor`, `ssrf`, `xss`). Extensions
(Autorize, Param Miner, Logger++) extend coverage. **High RAG value:** point at an authz/logic test
checklist and HackTricks web-testing notes so methodology lives in RAG, not this body.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Target confirmed in scope AND Burp Target scope restricted to in-scope hosts before testing
    verify: judge
    evidence: notes/scope.txt
    on_fail: fail
    required: true
  - id: app-mapped
    desc: App proxied/crawled; mapped endpoints captured (not assumed)
    verify: nonempty
    evidence: notes/sitemap.md
    on_fail: redo-part
    required: true
  - id: requests-tested
    desc: Interesting requests tested via Repeater/Intruder; run marker written
    verify: nonempty
    evidence: summary.txt
    on_fail: redo-skill
    required: true
  - id: evidence-exported
    desc: Notable request/response cases saved into the run directory
    verify: exists
    evidence: requests
    on_fail: redo-part
    required: false
```

## Notes / pitfalls
- **Scope first.** Setting Burp's Target scope to in-scope hosts only (and filtering Proxy/Logger to
  it) is mandatory before browsing — otherwise you capture/attack out-of-scope traffic;
  `scope-confirmed` fails hard (`on_fail: fail`).
- Much is manual and not reproduced by one command — capture evidence deliberately (save items,
  export report) as you go, not after.
- Hand injectable parameters to `sqlmap` (save item → `req.txt`); don't brute-force injection in
  Repeater by hand.
- Community Edition throttles Intruder and has no active scan — plan manual/targeted fuzzing
  accordingly.
- A run that finds nothing must still write `summary.txt` ("no findings recorded") and `findings.md`
  so "ran but empty" ≠ "didn't run".
- **Platform guardrail:** if a step is refused by a Claude Code safety classifier ("could not evaluate
  this action") or an API cyber safeguard (`invalid_request` / error `[cyber]`), STOP — write
  `_run.json` (`status: error`, block type + request id in `errors[]`) and `summary.txt` in the
  error-handback shape, then hand back. Never retry, reword, split, background, or otherwise bypass the
  block (see CLAUDE.md).
- Never write output under `skills/`; the run directory is always anchored to the repo root via
  `git rev-parse --show-toplevel` under `out/burpsuite/<timestamp>/` (git-ignored).
