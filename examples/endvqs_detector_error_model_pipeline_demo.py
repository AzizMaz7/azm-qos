from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import run_endvqs_detector_error_model_pipeline

print("AZM-QOS v1.9 END/VQS + Detector Error Model Pipeline Demo")
print("=" * 70)

result = run_endvqs_detector_error_model_pipeline(
    shots=64,
    repeats=1,
    n_rounds=5,
    n_trials=10,
    measurement_error_probability=0.05,
    seed=99,
)

print(result.summary())
print()
print("Detector error model:")
print(result.detector_error_model.summary())
print()
print("Matching benchmark:")
print(result.matching_benchmark_result.summary())
