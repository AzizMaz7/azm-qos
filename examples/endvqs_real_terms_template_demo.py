from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_endvqs import (
    load_component_registry_json,
    component_registry_to_term_registry,
    validate_term_registry,
    build_all_endvqs_workloads,
    assemble_m_matrix,
    assemble_v_vector,
)

print("AZM-QOS v1.1 Real-Terms Template Demo")
print("=" * 70)

template_path = ROOT / "templates" / "endvqs_real_terms_template.json"
component_registry = load_component_registry_json(template_path)
term_registry = component_registry_to_term_registry(component_registry)

print(component_registry.summary())
print()
print(validate_term_registry(term_registry).summary())

workloads = build_all_endvqs_workloads(registry=term_registry)
manager = RuntimeManager()
results = [manager.run(w, "shot_simulator", RuntimeConfig(shots=512, repeats=5, seed=11)) for w in workloads]

print()
print("M matrix from template terms:")
print(assemble_m_matrix(results, dimension=2))
print()
print("V vector from template terms:")
print(assemble_v_vector(results, dimension=2))
