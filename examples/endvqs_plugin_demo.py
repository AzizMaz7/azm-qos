from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import default_plugin_registry, RuntimeManager, RuntimeConfig, make_text_report

registry = default_plugin_registry()
manager = RuntimeManager()

workloads = registry.create_workloads("azmqos-endvqs-template", theta0=0.4, theta1=0.7)

print("AZM-QOS v0.6 END/VQS Plugin Demo")
print("=" * 70)
print("These are proxy workloads. Replace the proxy Pauli terms with real M and V decompositions.")

for workload in workloads:
    result = manager.run(workload, "shot_simulator", RuntimeConfig(shots=4096, repeats=25, seed=321))
    print()
    print(result.summary())
    print("Tags:", workload.tags)
    print("Metadata:", workload.metadata)
