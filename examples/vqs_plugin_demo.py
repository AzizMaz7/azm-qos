from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import default_plugin_registry, RuntimeManager, RuntimeConfig, ErrorManager

registry = default_plugin_registry()
manager = RuntimeManager()
error_manager = ErrorManager()

workloads = registry.create_workloads("azmqos-vqs-template", theta0=0.4, theta1=0.7)

print("AZM-QOS v0.6 VQS Plugin Demo")
print("=" * 70)

for workload in workloads:
    result = manager.run(workload, "shot_simulator", RuntimeConfig(shots=2048, repeats=25, seed=123))
    allocation = error_manager.allocate_shots(workload, total_shots=4096)
    print()
    print(result.summary())
    print(allocation.summary())
