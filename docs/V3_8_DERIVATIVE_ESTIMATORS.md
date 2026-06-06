# AZM-QOS v3.8 Parameter-Shift and Derivative Estimators

v3.8 adds parameter-shift and finite-difference derivative workflows for END/VQS state-preparation parameters.

## New file

```text
azmqos_research/derivative_estimators.py
```

## Main commands

```bash
azmqos derivative-demo --output-dir outputs/derivative_demo
```

Production derivative run:

```bash
azmqos production-derivatives --config outputs/production_project/azmqos_production.json --backend fallback
```

## Main outputs

- `derivative_estimates.csv`
- `derivative_estimates.json`
- `M_derivatives.csv`
- `V_derivatives.csv`
- `derivative_comparison.png`
- `derivative_report.md`
- `production_derivatives_manifest.json`
