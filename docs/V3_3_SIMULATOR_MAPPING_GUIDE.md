# AZM-QOS v3.3 Simulator Mapping Guide

The default v3.3 workload-to-circuit adapter maps each production workload to a one-qubit Ry circuit:

```text
|0> -- Ry(theta) -- measure Z
```

with `<Z> = cos(theta)`. This is a scaffold for validating execution/database/dashboard flow. For final END/VQS production, replace this mapping with circuits constructed from actual Pauli-term decompositions.
