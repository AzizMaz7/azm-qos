from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_endvqs import (
    default_component_registry_from_proxy_terms,
    component_registry_to_term_registry,
    validate_term_registry,
)

print("AZM-QOS v1.1 Component Registry Demo")
print("=" * 70)

component_registry = default_component_registry_from_proxy_terms()
term_registry = component_registry_to_term_registry(component_registry)

print(component_registry.summary())
print()
print(validate_term_registry(term_registry).summary())
