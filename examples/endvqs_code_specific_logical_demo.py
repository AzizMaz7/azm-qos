from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_endvqs import default_endvqs_registry, assemble_m_matrix, assemble_v_vector, build_all_endvqs_workloads
from azmqos_logical import repetition_code_3_logical_operator_map, encode_registry_with_code_map

print("AZM-QOS v1.3 END/VQS Code-Specific Logical Workload Demo")
print("=" * 70)

physical_registry = default_endvqs_registry()
code_map = repetition_code_3_logical_operator_map()
logical_registry = encode_registry_with_code_map(physical_registry, code_map)

workloads = build_all_endvqs_workloads(registry=logical_registry)
for workload in workloads:
    # Override to encoded zero-state scaffold.
    n = workload.n_qubits
    from azmqos.states import zero_state
    workload.state_preparation = lambda params, n=n: zero_state(n)
    workload.parameters = {"n_physical_qubits": n, "logical_code_map": code_map.name}

manager = RuntimeManager()
results = [manager.run(w, "shot_simulator", RuntimeConfig(shots=512, repeats=3, seed=13)) for w in workloads]

M = assemble_m_matrix(results, dimension=2)
V = assemble_v_vector(results, dimension=2)

print("Encoded M matrix:")
print(M)
print()
print("Encoded V vector:")
print(V)
