from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import make_generic_two_qubit_workload, RuntimeManager, RuntimeConfig

workload = make_generic_two_qubit_workload()
manager = RuntimeManager()

exact = manager.run(workload, "local_statevector", RuntimeConfig())
shot = manager.run(workload, "shot_simulator", RuntimeConfig(shots=8192, repeats=100, seed=321))

print("Backend comparison")
print("=" * 60)
print(exact.summary())
print(shot.summary())
print("Difference:", abs(shot.estimate_mean - exact.estimate_mean))
