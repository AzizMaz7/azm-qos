from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    counts_to_syndrome_bit,
    default_circuit_noise_spec,
    repetition_code_3,
    run_circuit_level_syndrome_benchmark,
    run_circuit_level_decoder_sweep,
    circuit_noise_sweep,
)
from azmqos_pipeline import run_endvqs_circuit_level_qec_pipeline

def test_counts_to_syndrome_bit():
    assert counts_to_syndrome_bit({"0": 7, "1": 3}) == 0
    assert counts_to_syndrome_bit({"0": 2, "1": 5}) == 1

def test_circuit_level_syndrome_benchmark():
    result = run_circuit_level_syndrome_benchmark(
        code_spec=repetition_code_3(),
        noise_spec=default_circuit_noise_spec(),
        n_rounds=3,
        shots=64,
        seed=1,
    )
    assert result.n_rounds == 3
    assert set(result.majority_syndrome_bits.keys())

def test_circuit_level_decoder_sweep():
    result = run_circuit_level_decoder_sweep(
        noise_specs=circuit_noise_sweep(two_qubit_errors=[0.0, 0.01], readout_error=0.02),
        n_trials=3,
        n_rounds=3,
        shots=64,
        seed=1,
    )
    assert len(result.points) == 2

def test_endvqs_circuit_level_pipeline():
    result = run_endvqs_circuit_level_qec_pipeline(
        shots=64,
        repeats=1,
        n_rounds=3,
        n_trials=3,
        seed=1,
    )
    assert result.M.shape == (2, 2)
    assert result.V.shape == (2,)
    assert len(result.circuit_decoder_sweep_result.points) == 3

if __name__ == "__main__":
    test_counts_to_syndrome_bit()
    test_circuit_level_syndrome_benchmark()
    test_circuit_level_decoder_sweep()
    test_endvqs_circuit_level_pipeline()
    print("All v1.7 circuit-level QEC benchmark tests passed.")
