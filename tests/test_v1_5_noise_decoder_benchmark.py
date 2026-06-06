from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    QECNoiseModel,
    measurement_noise_sweep,
    run_decoder_noise_sweep,
    estimate_pseudo_threshold,
)
from azmqos_pipeline import run_noise_aware_endvqs_qec_pipeline

def test_noise_model():
    model = QECNoiseModel(measurement_error_probability=0.1)
    model.validate()
    assert model.measurement_error_probability == 0.1

def test_noise_sweep_models():
    models = measurement_noise_sweep([0.0, 0.1])
    assert len(models) == 2
    assert models[1].measurement_error_probability == 0.1

def test_decoder_noise_sweep_runs():
    result = run_decoder_noise_sweep(
        probabilities=[0.0, 0.1],
        n_trials=5,
        n_rounds=3,
        shots=64,
        seed=1,
    )
    assert len(result.points) == 2
    assert result.points[0].failure_rate == 0.0

def test_noise_aware_pipeline_runs():
    result = run_noise_aware_endvqs_qec_pipeline(
        shots=64,
        repeats=1,
        syndrome_rounds=3,
        benchmark_trials=5,
        probabilities=[0.0, 0.1],
        seed=1,
    )
    assert result.encoded_pipeline_result.M.shape == (2, 2)
    assert len(result.decoder_benchmark_result.points) == 2

if __name__ == "__main__":
    test_noise_model()
    test_noise_sweep_models()
    test_decoder_noise_sweep_runs()
    test_noise_aware_pipeline_runs()
    print("All v1.5 noise decoder benchmark tests passed.")
