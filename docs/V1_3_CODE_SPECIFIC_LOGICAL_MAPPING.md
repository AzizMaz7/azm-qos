# AZM-QOS v1.3 Code-Specific Logical Mapping

v1.3 adds a more realistic logical operator layer.

## New file

```text
azmqos_logical/code_specific.py
```

## New concepts

```text
CodeSpecificLogicalOperatorMap
repetition_code_3_logical_operator_map
bell_pair_logical_operator_map
encode_registry_with_code_map
```

## Example

```python
from azmqos_endvqs import default_endvqs_registry
from azmqos_logical import repetition_code_3_logical_operator_map, encode_registry_with_code_map

physical = default_endvqs_registry()
code_map = repetition_code_3_logical_operator_map()
logical = encode_registry_with_code_map(physical, code_map)
```

## Scientific note

This is still a scaffold. The repetition-code map is more code-aware than the v1.2 block map, but production QEC requires code-specific logical operators, stabilizers, syndrome extraction, and decoder-aware execution.
