---
name: ssrf
description: >
  Use when testing for server-side request forgery (SSRF) on an authorized web target —
  parameters that make the server fetch a URL, cloud metadata (169.254.169.254), internal
  services, filter bypasses. A testing methodology (param ID → internal targets → bypass →
  impact) using an OOB collaborator and RAG payloads. Not for client-side XSS (use xss).
arguments: "target_or_urls [param]"
model: inherit
effort: medium
context: inline
agent:
category: web
domain: web
---

# ssrf — server-side request forgery testing methodology

Shared contract: see AGENTS.md.

## Goal
Identify server-side request forgery on an in-scope target, bypass any filtering, and prove impact
(internal service / cloud-metadata reachability) with a minimal, non-destructive proof-of-concept.

## Steps
1. Collect URL-fetching parameters. `RUN="$(python3 -I scripts/otus-log.py init --engagement "$ENGAGEMENT" --skill ssrf)"`; `python3 -I scripts/otus-log.py scope-check --engagement "$ENGAGEMENT" --target "$TARGET" --run-dir "$RUN"`; nonzero STOP. Check both the application and each induced destination/collaborator; never assume private/metadata IPs authorized. Use existing authorized OOB facilities, not a held local listener.
2. **Parameter identification.** Enumerate params/headers that trigger an outbound request; point each at your OOB host to confirm the server fetches attacker-controlled URLs. Record confirmed-fetching params in `notes/candidates.md`.
3. **Internal / metadata targets.** For confirmed SSRF, probe internal reachability — loopback (`127.0.0.1`), RFC1918 ranges, link-local **cloud metadata** (`169.254.169.254`, AWS/GCP/Azure IMDS paths) — to demonstrate reach only. Log attempts.
4. **Filter bypass (RAG-driven).** When blocked, apply documented bypasses — alternate IP encodings (decimal/octal/hex), DNS rebinding, redirect chains, `[::]`/IPv6, scheme/wrapper tricks — from the shared RAG (PayloadsAllTheThings/SSRF + HackTricks); do **not** hardcode a payload library here.
5. Every CLI request uses `python3 -I scripts/otus-log.py run --run-dir "$RUN" --target "$TARGET" --target "$DESTINATION" -- <original argv>`; manual tests save exports and marker events. Confirm only minimal callback/banner reach, never full credentials. Save param/payload/impact proof. `python3 -I scripts/otus-log.py finish --run-dir "$RUN" --status "$STATUS" --summary "$SUMMARY" --item 'scope-confirmed=ok:../../scope.json' --item 'params-identified=ok:notes/candidates.md' --item 'tested=ok:findings.md' --item 'confirmed-impact=ok:findings.md'`; add verified `--finding` entries and cleanup fields, or summary `no ssrf confirmed`.

## Modern tooling & alternatives
Burp Suite (Repeater + Collaborator) is the manual hub; `interactsh` for standalone OOB; param
discovery via `ffuf`/`katana`/Param Miner. `nuclei` SSRF templates catch known patterns — this skill
covers the manual/bypass reasoning those miss.

## Checklist
```yaml
checklist:
  - id: scope-confirmed
    desc: Explicit engagement authorization, application, and induced destinations checked
    verify: judge
    evidence: ../../scope.json
    on_fail: fail
    required: true
  - id: params-identified
    desc: Parameters that trigger server-side outbound requests enumerated
    verify: nonempty
    evidence: notes/candidates.md
    on_fail: redo-part
    required: true
  - id: tested
    desc: SSRF testing executed (internal/metadata targets + bypasses); run marker written
    verify: nonempty
    evidence: findings.md
    on_fail: redo-skill
    required: true
  - id: confirmed-impact
    desc: Confirmed SSRF has OOB/response proof + minimal impact, no secret exfil (or documented "none")
    verify: judge
    evidence: findings.md
    on_fail: fail
    required: true
```

## Notes / pitfalls
- **Minimal proof only.** Show reach (callback, metadata endpoint, internal banner) — never dump full cloud credentials or pivot destructively; `confirmed-impact` fails hard (`on_fail: fail`).
- Blind SSRF needs an OOB collaborator — a filtered reflected response does not mean "not vulnerable"; check your listener.
- Keep bypass payloads in RAG (encodings, rebinding, redirects), not inline, so they stay current.
- No SSRF still finishes with that summary; findings.md is generated.
