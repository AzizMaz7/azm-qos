# AZM-QOS v3.5 Production Pauli Execution

v3.5 connects the Pauli compiler to the production execution/database/dashboard system.

## Main command

```bash
azmqos production-pauli-execute --config outputs/production_project/azmqos_production.json
```

Options:

```bash
azmqos production-pauli-execute --config outputs/production_project/azmqos_production.json --shots 2048 --max-components 4
```

## Main outputs

- `grouped_counts.json`
- `grouped_counts.csv`
- `component_estimates.csv`
- `M_estimates.csv`
- `V_estimates.csv`
- `mv_estimate_report.md`
- production Pauli execution database
- dashboard
- `production_pauli_execution_report.md`
