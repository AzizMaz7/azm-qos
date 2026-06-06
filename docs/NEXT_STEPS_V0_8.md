# Next Steps: AZM-QOS Core v0.8

Recommended next milestone:

## Real END/VQS Plugin Implementation

v0.6 gave us the plugin system.
v0.7 gave us IBM Runtime scaffolding.

v0.8 should now implement a more serious `azmqos-endvqs` plugin.

Add:

- M-matrix workload builder
- V-vector workload builder
- Pauli decomposition registry
- M/V assembly from JobResult objects
- shot-scaling benchmark for M and V
- QEC-compatible logical observable placeholder

## Target plugin structure

```text
azmqos_endvqs/
   ├── __init__.py
   ├── terms.py
   ├── builders.py
   ├── assemblers.py
   ├── benchmarks.py
   └── reports.py
```
