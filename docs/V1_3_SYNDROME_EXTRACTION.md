# AZM-QOS v1.3 Syndrome Extraction

v1.3 adds hardware-independent syndrome-extraction circuit specifications.

## New file

```text
azmqos_qec/syndrome_circuits.py
```

## Main objects

```text
StabilizerMeasurementStep
SyndromeExtractionCircuitSpec
```

## Main functions

```text
build_syndrome_extraction_spec
build_syndrome_extraction_specs_for_code
syndrome_spec_to_qiskit
```

## Scaffold rule

- Z stabilizers: CNOT(data -> ancilla)
- X stabilizers: H basis change, then CNOT(data -> ancilla)
- Y stabilizers: Sdg + H basis change, then CNOT(data -> ancilla)

Production fault-tolerant syndrome extraction must add repeated rounds, scheduling, hook-error suppression, measurement noise, and hardware-connectivity constraints.
