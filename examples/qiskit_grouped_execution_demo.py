from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    PauliTerm,
    PauliComponent,
    QiskitExecutionConfig,
    execute_component_with_qiskit_or_fallback,
)

print("AZM-QOS v3.6 Qiskit/Fallback Grouped Execution Demo")
print("=" * 70)

component = PauliComponent(
    name="demo_grouped_qiskit_component",
    quantity="M",
    indices=[0, 0],
    terms=[
        PauliTerm(0.5, "ZI"),
        PauliTerm(-0.25, "IZ"),
        PauliTerm(0.125, "ZZ"),
        PauliTerm(0.1, "XX"),
    ],
    metadata={"component_family": "Mbb"},
)

config = QiskitExecutionConfig(backend="auto", shots=512)
result = execute_component_with_qiskit_or_fallback(component, config)

print(result.summary())
print()
for group in result.group_results:
    print(group.summary())
    print()
