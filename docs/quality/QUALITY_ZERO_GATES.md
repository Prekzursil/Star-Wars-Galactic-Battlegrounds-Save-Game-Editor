# Quality Zero Gates

This repository is configured for strict quality enforcement:

- Coverage target: 100% (project + patch)
- Mandatory zero-open findings: Sonar, Codacy, Semgrep, Sentry, DeepScan
- Fail-closed secrets preflight
- Aggregated required-context assertion via `Quality Zero Gate`

If required tokens/variables are missing, workflows fail by design.
