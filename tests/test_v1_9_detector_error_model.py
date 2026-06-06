from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    build_repetition_detector_graph,
    detector_graph_to_error_model,
    run_matching_decoder_benchmark,
)
from azmqos_pipeline import run_endvqs_detector_error_model_pipeline

def test_detector_error_model_export():
    graph = build_repetition_detector_graph(["S_ZZI", "S_IZZ"], n_rounds=3, measurement_error_probability=0.05)
    model = detector_graph_to_error_model(graph, default_probability=0.05, logical_labels={"0": "logical"})
    assert len(model.detector_id_map) == 6
    assert len(model.instructions) > 0
    assert "error(" in model.to_text()

def test_matching_benchmark():
    result = run_matching_decoder_benchmark(probabilities=[0.0, 0.05], n_trials=5, n_rounds=3, seed=1)
    assert len(result.points) == 2
    assert result.points[0].logical_failure_rate == 0.0

def test_detector_error_model_pipeline():
    result = run_endvqs_detector_error_model_pipeline(shots=64, repeats=1, n_rounds=3, n_trials=5, seed=1)
    assert result.detector_graph_pipeline_result.circuit_pipeline_result.M.shape == (2, 2)
    assert len(result.detector_error_model.instructions) > 0
    assert len(result.matching_benchmark_result.points) == 3

if __name__ == "__main__":
    test_detector_error_model_export()
    test_matching_benchmark()
    test_detector_error_model_pipeline()
    print("All v1.9 detector-error-model tests passed.")
