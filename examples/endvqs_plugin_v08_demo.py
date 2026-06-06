from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig, PluginRegistry
from azmqos_endvqs import (
    ENDVQSWorkloadPlugin,
    build_all_endvqs_workloads,
    default_endvqs_registry,
    ENDVQSParameterPoint,
    assemble_m_matrix,
    assemble_v_vector,
    assembled_results_summary,
)

print("AZM-QOS v0.8 END/VQS Plugin Demo")
print("=" * 70)

registry = default_endvqs_registry()
print(registry.summary())

parameter_point = ENDVQSParameterPoint(theta0=0.4, theta1=0.7, label="demo_point")
workloads = build_all_endvqs_workloads(registry=registry, parameter_point=parameter_point)

manager = RuntimeManager()
results = []
for workload in workloads:
    result = manager.run(workload, "shot_simulator", RuntimeConfig(shots=2048, repeats=20, seed=123))
    results.append(result)
    print(result.summary())

M = assemble_m_matrix(results, dimension=registry.dimension)
V = assemble_v_vector(results, dimension=registry.dimension)

print()
print(assembled_results_summary(M, V))

# Demonstrate plugin registry integration.
plugin_registry = PluginRegistry()
plugin_registry.register(ENDVQSWorkloadPlugin())
print()
print("Registered plugin:", list(plugin_registry.list_plugins().keys()))
