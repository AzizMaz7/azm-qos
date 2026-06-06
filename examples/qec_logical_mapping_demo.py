from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    PauliTerm,
    PauliComponent,
    default_repetition_code,
    map_component_to_logical,
)

print("AZM-QOS v4.1 QEC Logical Mapping Demo")
print("=" * 70)

code = default_repetition_code(3)
component = PauliComponent(
    name="demo_mapping_component",
    quantity="M",
    indices=[0, 0],
    terms=[
        PauliTerm(0.5, "ZI"),
        PauliTerm(-0.25, "IZ"),
        PauliTerm(0.1, "XX"),
    ],
    metadata={"component_family": "Mbb"},
)

logical = map_component_to_logical(component, code)

print(code.summary())
print()
print(logical.summary())
for term in logical.logical_terms:
    print(term.summary())
