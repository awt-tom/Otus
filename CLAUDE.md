# Otus runtime routing
- Recon tasks (subfinder, httpx, port-scanner, ffuf) → delegate to the `recon-runner` subagent.
- Scanning/exploitation (nuclei, web-vuln classes, exploitation) → delegate to the `vuln-hunter` subagent.
- After every skill run, hand the run dir to the `reviewer` subagent (which reads the `review` skill) before results are final.
- All work is lab/authorized only. Agents must confirm scope before any active step.
