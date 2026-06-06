# AZM-QOS Core v0.4 Qiskit Adapter

v0.4 adds optional Qiskit support.

## New files

```text
azmqos/qiskit_adapter.py
azmqos/qiskit_backends.py
examples/qiskit_circuit_demo.py
examples/qiskit_qasm_export_demo.py
```

## Main features

- Build a `QuantumWorkload` from a Qiskit `QuantumCircuit`
- Convert Pauli terms to `SparsePauliOp`
- Export Qiskit circuits to QASM when supported by installed Qiskit version
- Run circuit workloads on `QiskitAerBackend`
- Measure each Pauli string through basis-rotated measurement circuits

## Installation

```bash
python -m pip install qiskit qiskit-aer
```

## Design rule

Qiskit is an adapter, not the core. The core abstractions remain:

```text
QuantumWorkload
RuntimeManager
BackendAdapter
JobResult
```
