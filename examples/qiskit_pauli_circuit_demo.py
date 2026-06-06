from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    PauliTerm,
    PauliComponent,
    compile_pauli_component,
    build_circuit_or_fallback_spec,
    qiskit_is_available,
)

print("AZM-QOS v3.6 Qiskit Pauli Circuit Demo")
print("=" * 70)

component = PauliComponent(
    name="demo_qiskit_component",
    quantity="M",
    indices=[0, 0],
    terms=[PauliTerm(1.0, "ZI"), PauliTerm(0.5, "IZ"), PauliTerm(0.25, "XX")],
    metadata={"component_family": "Mbb"},
)

compiled = compile_pauli_component(component)

print("Qiskit available:", qiskit_is_available())
print(compiled.summary())
print()

for group in compiled.groups:
    spec, build, qc = build_circuit_or_fallback_spec(component, group)
    print(build.summary())
    print(build.circuit_repr)
    print()
