from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import run_endvqs_detector_graph_pipeline

print("AZM-QOS v1.8 END/VQS + Detector Graph Pipeline Demo")
print("=" * 70)

result = run_endvqs_detector_graph_pipeline(
    shots=64,
    repeats=1,
    n_rounds=5,
    n_trials=3,
    measurement_error_probability=0.05,
    seed=123,
)

print(result.summary())
print()
print("Detector graph:")
print(result.detector_graph.summary())
print()
print("Matching:")
print(result.matching_result.summary())
