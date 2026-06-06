from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    repetition_code_3,
    run_repeated_syndrome_rounds,
    repeated_syndrome_to_syndrome_result,
    run_decoder_aware_qec_execution,
)
from azmqos_pipeline import run_endvqs_logical_decoder_pipeline

def test_repeated_rounds():
    result = run_repeated_syndrome_rounds(
        repetition_code_3(),
        n_rounds=3,
        backend_name="local_statevector",
        shots=64,
        seed=1,
        measurement_error_probability=0.0,
    )
    assert result.n_rounds == 3
    assert all(bit == 0 for bit in result.majority_syndrome_bits.values())

def test_repeated_to_syndrome():
    repeated = run_repeated_syndrome_rounds(repetition_code_3(), n_rounds=3, shots=64, seed=1)
    syndrome = repeated_syndrome_to_syndrome_result(repeated)
    assert syndrome.syndrome_bits == repeated.majority_syndrome_bits

def test_decoder_aware_execution():
    result = run_decoder_aware_qec_execution(
        repetition_code_3(),
        n_rounds=3,
        shots=64,
        seed=1,
        measurement_error_probability=0.0,
    )
    assert result.decoder_result.correction == "I"
    assert len(result.correction_history) == 1

def test_logical_decoder_pipeline():
    result = run_endvqs_logical_decoder_pipeline(
        shots=64,
        repeats=1,
        syndrome_rounds=3,
        measurement_error_probability=0.0,
        seed=1,
    )
    assert result.M.shape == (2, 2)
    assert result.V.shape == (2,)
    assert result.decoder_execution_result.decoder_result.correction == "I"

if __name__ == "__main__":
    test_repeated_rounds()
    test_repeated_to_syndrome()
    test_decoder_aware_execution()
    test_logical_decoder_pipeline()
    print("All v1.4 repeated syndrome/decoder tests passed.")
