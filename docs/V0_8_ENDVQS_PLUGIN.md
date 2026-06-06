# AZM-QOS Core v0.8 END/VQS Plugin

v0.8 adds the first separated END/VQS plugin package:

```text
azmqos_endvqs
```

## Package structure

```text
azmqos_endvqs/
   ├── __init__.py
   ├── terms.py
   ├── builders.py
   ├── assemblers.py
   ├── benchmarks.py
   ├── reports.py
   └── plugin.py
```

## Main idea

The core remains general. END/VQS-specific science lives in the plugin.

## Current status

The default Pauli terms are proxy terms. They validate:

- M-workload construction
- V-workload construction
- backend execution
- M-matrix assembly
- V-vector assembly
- report generation

## What to replace next

Replace proxy terms in `terms.py` with real derived Pauli decompositions for:

```text
Mbb
Mab
Maa
Va
Vb
```

## Example

```python
from azmqos_endvqs import run_endvqs_benchmark

data = run_endvqs_benchmark(shots=4096, repeats=25)
print(data["M"])
print(data["V"])
```
