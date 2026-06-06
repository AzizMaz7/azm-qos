# How to Replace Proxy END/VQS Terms with Real Research Terms

Open:

```text
azmqos_endvqs/terms.py
```

Replace the default registry:

```python
m_terms = {
    (0, 0): [...],
    (0, 1): [...],
    ...
}

v_terms = {
    0: [...],
    1: [...],
    ...
}
```

with terms from your derivation.

Each term must be:

```python
PauliTerm(coefficient, "PAULI_STRING", label="descriptive_name")
```

Example:

```python
PauliTerm(-0.5, "XX", label="Mab_P1P2_component")
```

Then run:

```bash
python examples\endvqs_benchmark_demo.py
```

The assembler will produce:

```text
M matrix
V vector
```

from the workload results.
