from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from azmqos import PauliTerm, expectation_value, RuntimeManager, RuntimeConfig, make_generic_two_qubit_workload
from azmqos.states import zero_state, bell_state

def test_z_zero():
    assert np.isclose(expectation_value(zero_state(1), PauliTerm(1, "Z")), 1.0)

def test_bell_zz():
    assert np.isclose(expectation_value(bell_state(), PauliTerm(1, "ZZ")), 1.0)

def test_statevector_backend():
    workload = make_generic_two_qubit_workload()
    result = RuntimeManager().run(workload, "local_statevector", RuntimeConfig())
    assert result.backend_type == "statevector"
    assert result.mean_absolute_error == 0.0

def test_shot_backend():
    workload = make_generic_two_qubit_workload()
    result = RuntimeManager().run(workload, "shot_simulator", RuntimeConfig(shots=128, repeats=2, seed=1))
    assert result.backend_type == "shot_simulator"
    assert result.shots == 128

if __name__ == "__main__":
    test_z_zero()
    test_bell_zz()
    test_statevector_backend()
    test_shot_backend()
    print("All direct tests passed.")
