from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig, make_generic_two_qubit_workload

workload = make_generic_two_qubit_workload()
manager = RuntimeManager()

print("AZM-QOS v0.7 IBM Safe Failure Demo")
print("=" * 70)

try:
    result = manager.run(workload, "ibm_runtime", RuntimeConfig(shots=1024, repeats=1))
    print(result.summary())
except Exception as exc:
    print("IBM backend did not submit a job, as expected in v0.7 scaffold mode.")
    print()
    print(str(exc))
