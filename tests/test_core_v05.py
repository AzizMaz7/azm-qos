from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from azmqos import (
    PauliTerm,
    expectation_value,
    RuntimeManager,
    RuntimeConfig,
    make_generic_two_qubit_workload,
    bootstrap_confidence_interval,
    variance_aware_shot_allocation,
    ReadoutMitigationModel,
    linear_zero_noise_extrapolation,
)
from azmqos.states import zero_state, bell_state

def test_z_zero():
    assert np.isclose(expectation_value(zero_state(1), PauliTerm(1, "Z")), 1.0)

def test_bell_zz():
    assert np.isclose(expectation_value(bell_state(), PauliTerm(1, "ZZ")), 1.0)

def test_shot_backend():
    workload = make_generic_two_qubit_workload()
    result = RuntimeManager().run(workload, "shot_simulator", RuntimeConfig(shots=128, repeats=2, seed=1))
    assert result.backend_type == "shot_simulator"

def test_bootstrap_ci():
    ci = bootstrap_confidence_interval([1.0, 1.1, 0.9, 1.05], n_resamples=100, seed=1)
    assert ci.lower <= ci.mean <= ci.upper

def test_shot_allocation():
    workload = make_generic_two_qubit_workload()
    allocation = variance_aware_shot_allocation(workload, total_shots=1000)
    assert sum(allocation.per_term.values()) == 1000

def test_readout_mitigation():
    model = ReadoutMitigationModel([[0.97, 0.03], [0.05, 0.95]])
    corrected = model.mitigate_z_expectation(0.8)
    assert -1.0 <= corrected <= 1.0

def test_zne():
    zne = linear_zero_noise_extrapolation([1, 2, 3], [0.9, 0.8, 0.7])
    assert isinstance(zne.extrapolated_zero_noise, float)

if __name__ == "__main__":
    test_z_zero()
    test_bell_zz()
    test_shot_backend()
    test_bootstrap_ci()
    test_shot_allocation()
    test_readout_mitigation()
    test_zne()
    print("All v0.5 direct tests passed.")
