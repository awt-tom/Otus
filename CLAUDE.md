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
