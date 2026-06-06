from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig, PluginRegistry
from azmqos_qec import QECWorkloadPlugin, repetition_code_3, build_all_qec_workloads

print("AZM-QOS v0.9 QEC Plugin Demo")
print("=" * 70)

code = repetition_code_3()
print(code.summary())

workload_set = build_all_qec_workloads(code)
manager = RuntimeManager()

for workload in workload_set.all_workloads:
    result = manager.run(workload, "local_statevector", RuntimeConfig())
    print(result.summary())
    print("  terms:", result.term_estimates)

registry = PluginRegistry()
registry.register(QECWorkloadPlugin())
print()
print("Registered plugin:", list(registry.list_plugins().keys()))
