# AZM-QOS v3.7 END/VQS State-Preparation Hooks

v3.7 adds END/VQS state-preparation scaffolds and connects them to the v3.6 Qiskit/fallback Pauli execution layer.

## New file

```text
azmqos_research/endvqs_stateprep.py
```

## Main commands

```bash
azmqos endvqs-stateprep-demo --output-dir outputs/endvqs_stateprep_demo
```

Production execution with state-preparation hooks:

```bash
azmqos production-endvqs-execute --config outputs/production_project/azmqos_production.json --backend fallback
```

## Main outputs

- `stateprep_config.json`
- `stateprep_plan.json`
- `stateprep_operations.csv`
- `stateprep_report.md`
- `endvqs_execution_results.csv`
- `endvqs_execution_results.json`
- `endvqs_stateprep_execution_report.md`
