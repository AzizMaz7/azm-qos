from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import default_plugin_registry, RuntimeManager, RuntimeConfig

registry = default_plugin_registry()
manager = RuntimeManager()

print("AZM-QOS v0.6 QEC Plugin Demo")
print("=" * 70)

for state in ["bell", "ghz"]:
    workload = registry.create_workloads("azmqos-qec-template", state=state)
    result = manager.run(workload, "local_statevector", RuntimeConfig())
    print()
    print(result.summary())
    print("Term estimates:", result.term_estimates)
