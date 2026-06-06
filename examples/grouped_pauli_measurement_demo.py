from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import PauliTerm, PauliComponent, execute_component_pauli_measurements
print("AZM-QOS v3.5 Grouped Pauli Measurement Demo")
print("=" * 70)
component = PauliComponent(name="demo_grouped_component", quantity="M", indices=[0, 0], terms=[PauliTerm(0.5, "ZI"), PauliTerm(-0.25, "IZ"), PauliTerm(0.125, "ZZ"), PauliTerm(0.1, "XX"), PauliTerm(0.05, "YY")], metadata={"component_family": "Mbb"})
compilation, estimate = execute_component_pauli_measurements(component, shots_per_group=512)
print(compilation.summary())
print()
print(estimate.summary())
print()
for group_result in estimate.grouped_results:
    print(group_result.summary())
