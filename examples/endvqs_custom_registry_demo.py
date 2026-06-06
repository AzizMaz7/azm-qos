from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import PauliTerm, RuntimeManager, RuntimeConfig
from azmqos_endvqs import (
    create_custom_registry,
    ENDVQSParameterPoint,
    build_all_endvqs_workloads,
    assemble_m_matrix,
    assemble_v_vector,
)

print("AZM-QOS v0.8 Custom END/VQS Registry Demo")
print("=" * 70)

# Replace these with your real derived Pauli decompositions.
custom_registry = create_custom_registry(
    m_terms={
        (0, 0): [PauliTerm(1.0, "ZI", "custom_M00")],
        (0, 1): [PauliTerm(-0.5, "XX", "custom_M01")],
        (1, 0): [PauliTerm(-0.5, "XX", "custom_M10")],
        (1, 1): [PauliTerm(1.0, "IZ", "custom_M11")],
    },
    v_terms={
        0: [PauliTerm(0.75, "XX", "custom_V0")],
        1: [PauliTerm(-0.25, "YY", "custom_V1")],
    },
    type="custom_demo",
)

workloads = build_all_endvqs_workloads(
    registry=custom_registry,
    parameter_point=ENDVQSParameterPoint(theta0=0.3, theta1=0.5, label="custom_demo_point"),
)

manager = RuntimeManager()
results = [manager.run(w, "shot_simulator", RuntimeConfig(shots=1024, repeats=10, seed=7)) for w in workloads]

print("M matrix:")
print(assemble_m_matrix(results, dimension=2))
print("V vector:")
print(assemble_v_vector(results, dimension=2))
