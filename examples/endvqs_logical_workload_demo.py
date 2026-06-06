from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_endvqs import default_endvqs_registry, assemble_m_matrix, assemble_v_vector
from azmqos_logical import repetition_code_block_encoding, build_logical_endvqs_workloads

print("AZM-QOS v1.2 Encoded END/VQS Workload Demo")
print("=" * 70)

registry = default_endvqs_registry()
encoding = repetition_code_block_encoding(block_size=3)
workloads = build_logical_endvqs_workloads(registry, encoding)

manager = RuntimeManager()
results = []
for workload in workloads:
    result = manager.run(workload, "shot_simulator", RuntimeConfig(shots=512, repeats=3, seed=5))
    results.append(result)
    print(result.summary())

M = assemble_m_matrix(results, dimension=2)
V = assemble_v_vector(results, dimension=2)

print()
print("Encoded-workload M matrix:")
print(M)
print()
print("Encoded-workload V vector:")
print(V)
