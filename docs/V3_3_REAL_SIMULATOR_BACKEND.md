# AZM-QOS v3.3 Real Simulator Backend Integration

v3.3 adds simulator execution integration for production workloads.

## New file

```text
azmqos_research/production_simulator.py
```

## Main commands

```bash
azmqos production-simulate --config outputs/production_project/azmqos_production.json
azmqos production-shot-scaling --config outputs/production_project/azmqos_production.json
```

## Backend modes

- `auto`: use Qiskit/Aer if available, fallback otherwise
- `aer`: require Qiskit/Aer or Qiskit simulator
- `fallback`: dependency-free deterministic simulator
