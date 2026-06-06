# AZM-QOS v4.0 Stable Integrated Platform

v4.0 combines the major AZM-QOS workflows into one stable platform.

## Required first command

Always initialize the production project first:

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

This creates:

```text
outputs\production_project\azmqos_production.json
```

Then run:

```powershell
azmqos stable-run --config outputs\production_project\azmqos_production.json --backend fallback --max-components 2 --shots 64
```

## New file

```text
azmqos_research/stable_platform.py
```

## Stable workflow steps

1. Production plan
2. Grouped Pauli execution
3. Qiskit/fallback Pauli execution
4. END/VQS state-preparation execution
5. Derivative estimation
6. Derivative mitigation
7. Dashboard export
8. Manuscript scaffold
9. Reproducibility archive
