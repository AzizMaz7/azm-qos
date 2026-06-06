# AZM-QOS v1.2 Logical Observable Mapping

v1.2 adds:

```text
azmqos_logical
```

## Main purpose

Map END/VQS Pauli observables into QEC/logical Pauli observables.

## Default scaffold

```text
I -> III
X -> XXX
Y -> YYY
Z -> ZZZ
```

for a 3-qubit repetition-code block.

## New modules

```text
azmqos_logical/encodings.py
azmqos_logical/mapper.py
azmqos_logical/workloads.py
azmqos_logical/resources.py
azmqos_logical/reports.py
```

## Next serious scientific step

Replace the simple block map with code-specific logical Pauli operators and syndrome-extraction circuits.
