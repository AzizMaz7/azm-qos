# AZM-QOS v3.6 Qiskit Execution of Compiled Pauli Circuits

v3.6 adds Qiskit/fallback execution for grouped Pauli measurement circuits.

## New file

```text
azmqos_research/qiskit_pauli_execution.py
```

## Main command

```bash
azmqos production-qiskit-execute --config outputs/production_project/azmqos_production.json
```

Fallback mode:

```bash
azmqos production-qiskit-execute --config outputs/production_project/azmqos_production.json --backend fallback
```

Hardware dry-run mode:

```bash
azmqos production-qiskit-execute --config outputs/production_project/azmqos_production.json --backend hardware_dry_run --hardware-backend-name ibm_fez
```

## Main outputs

- `qiskit_group_results.json`
- `qiskit_group_results.csv`
- `circuit_builds.json`
- `component_estimates.csv`
- `M_estimates.csv`
- `V_estimates.csv`
- `qiskit_execution_report.md`
- database and dashboard artifacts
