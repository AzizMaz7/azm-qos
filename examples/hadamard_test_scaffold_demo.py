from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import PauliTerm, make_hadamard_test_specs, ancilla_expectation_from_counts

print("AZM-QOS v3.4 Hadamard-Test Scaffold Demo")
print("=" * 70)

terms = [
    PauliTerm(0.5, "XZI", label="demo_0"),
    PauliTerm(-0.25, "YYZ", label="demo_1"),
]

specs = make_hadamard_test_specs(terms, phase=0.0)

for spec in specs:
    print(spec.summary())
    print()

counts = {"0": 760, "1": 264}
print("Example ancilla expectation:", ancilla_expectation_from_counts(counts))
