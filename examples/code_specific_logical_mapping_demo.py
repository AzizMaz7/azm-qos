from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_endvqs import default_endvqs_registry
from azmqos_logical import (
    repetition_code_3_logical_operator_map,
    encode_registry_with_code_map,
    compare_registry_sizes,
)

print("AZM-QOS v1.3 Code-Specific Logical Mapping Demo")
print("=" * 70)

physical = default_endvqs_registry()
code_map = repetition_code_3_logical_operator_map()
logical = encode_registry_with_code_map(physical, code_map)

print(code_map.summary())
print()
print("Physical vs encoded registry sizes:")
print(compare_registry_sizes(physical, logical))

print()
print("Example encoded M(0,0) terms:")
for term in logical.get_m_terms(0, 0):
    print(f"  {term.name}: {term.coeff.real:+.6f} * {term.pauli}")
