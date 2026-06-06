# AZM-QOS v3.9 Error Mitigation for Derivative Estimators

v3.9 adds readout mitigation, ZNE-style extrapolation, uncertainty propagation, and shot-allocation scaffolds for derivative estimators.

## New file

```text
azmqos_research/derivative_mitigation.py
```

## Main commands

```bash
azmqos derivative-mitigation-demo --output-dir outputs/derivative_mitigation_demo
```

Production mitigated derivatives:

```bash
azmqos production-mitigated-derivatives --config outputs/production_project/azmqos_production.json --backend fallback
```

## Main outputs

- `raw_derivatives.csv`
- `raw_derivatives.json`
- `mitigated_derivatives.csv`
- `mitigated_derivatives.json`
- `M_mitigated_derivatives.csv`
- `V_mitigated_derivatives.csv`
- `mitigation_comparison.png`
- `derivative_mitigation_report.md`
- `production_mitigated_derivatives_manifest.json`
