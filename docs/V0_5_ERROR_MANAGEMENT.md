# AZM-QOS Core v0.5 Error Management Layer

v0.5 adds the first architecture for uncertainty and error management.

## New modules

```text
azmqos/uncertainty.py
azmqos/shot_allocation.py
azmqos/mitigation.py
azmqos/error_manager.py
```

## New capabilities

### Bootstrap uncertainty

Use repeated estimates to compute confidence intervals:

```python
ci = bootstrap_confidence_interval(samples)
```

### Adaptive shot allocation

Allocate a fixed measurement budget using:

```python
uniform_shot_allocation
coefficient_weighted_shot_allocation
variance_aware_shot_allocation
```

### Readout mitigation placeholder

A simple single-qubit confusion-matrix model is included as a scaffold.

### Zero-noise extrapolation placeholder

A linear ZNE utility is included as a scaffold.

## Design rule

The Error Management Layer should remain independent of any one project.
END/VQS, VQE, QAOA, QEC, and chemistry plugins can all use the same uncertainty and mitigation infrastructure.
