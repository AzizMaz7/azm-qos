# AZM-QOS v1.6 Circuit-Level Noise

v1.6 adds hardware-independent circuit-noise specifications and optional Qiskit Aer adapters.

## New files

```text
azmqos_qec/circuit_noise.py
azmqos_qec/qiskit_noise.py
azmqos_pipeline/circuit_noise_pipeline.py
```

## Noise specs

```text
DepolarizingNoiseSpec
ReadoutNoiseSpec
CircuitNoiseModelSpec
```

## Optional Qiskit Aer

If `qiskit-aer` is installed, AZM-QOS can build a Qiskit Aer `NoiseModel`.

Otherwise, the package still runs with scaffold estimates.
