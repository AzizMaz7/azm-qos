# AZM-QOS v3.4 Pauli Measurement Guide

For a Pauli string:

```text
X -> apply H, then Z-basis measurement
Y -> apply Sdg then H, then Z-basis measurement
Z -> direct Z-basis measurement
I -> ignored
```

The compiler groups terms that can share a single product measurement basis.

Hadamard-test specs are also generated for term-by-term ancilla measurement scaffolds.
