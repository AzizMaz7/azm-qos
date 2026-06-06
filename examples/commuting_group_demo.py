from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    PauliTerm,
    group_commuting_terms_greedy,
    basis_rotations_for_pauli_basis,
)

print("AZM-QOS v3.4 Commuting Group Demo")
print("=" * 70)

terms = [
    PauliTerm(1.0, "ZI"),
    PauliTerm(1.0, "IZ"),
    PauliTerm(1.0, "ZZ"),
    PauliTerm(1.0, "XX"),
    PauliTerm(1.0, "YY"),
]

groups = group_commuting_terms_greedy(terms)

for group in groups:
    print(group.summary())
    print("  rotations:", basis_rotations_for_pauli_basis(group.measurement_basis))
