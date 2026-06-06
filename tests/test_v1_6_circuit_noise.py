from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    default_circuit_noise_spec,
    circuit_noise_sweep,
    estimate_noisy_syndrome_probability_scaffold,
    repetition_code_3,
    build_syndrome_extraction_specs_for_code,
)
from azmqos_pipeline import compare_circuit_noise_to_syndrome_noise

def test_circuit_noise_spec():
    spec = default_circuit_noise_spec()
    spec.validate()
    assert spec.depolarizing.two_qubit_error == 0.01

def test_noise_sweep():
    specs = circuit_noise_sweep([0.0, 0.01], readout_error=0.02)
    assert len(specs) == 2
    assert specs[1].depolarizing.two_qubit_error == 0.01

def test_scaffold_probability():
    spec = default_circuit_noise_spec()
    p = estimate_noisy_syndrome_probability_scaffold(spec, stabilizer_weight=2)
    assert 0.0 <= p <= 1.0

def test_syndrome_specs_still_work():
    specs = build_syndrome_extraction_specs_for_code(repetition_code_3())
    assert len(specs) == 2

def test_noise_comparison_pipeline():
    result = compare_circuit_noise_to_syndrome_noise(n_trials=3, n_rounds=3, shots=64, seed=1)
    assert len(result.points) > 0

if __name__ == "__main__":
    test_circuit_noise_spec()
    test_noise_sweep()
    test_scaffold_probability()
    test_syndrome_specs_still_work()
    test_noise_comparison_pipeline()
    print("All v1.6 circuit-noise tests passed.")
