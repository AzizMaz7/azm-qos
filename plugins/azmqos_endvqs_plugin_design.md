# END/VQS Plugin Design

The END/VQS plugin should contain project-specific science, while the core stays general.

## Plugin responsibilities

- define END/VQS Pauli decompositions
- build M-matrix workloads
- build V-vector workloads
- assemble M and V from JobResult objects
- export thesis/manuscript-ready tables
- connect to QEC/logical observable layer later

## Do not put these into the core

```text
Mbb
Mab
Va
Vb
Fukutome representation
coherent-state nuclear representation
END-specific equations
```

These belong in `azmqos-endvqs`.
