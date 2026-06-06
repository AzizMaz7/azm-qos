from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    DetectorNode,
    DetectorEvent,
    build_repetition_detector_graph,
    syndrome_history_to_detector_events,
    decode_detector_events,
    GreedyMatchingDecoder,
)
from azmqos_pipeline import run_endvqs_detector_graph_pipeline

class Record:
    def __init__(self, round_index, bits):
        self.round_index = round_index
        self.syndrome_bits = bits

def test_detector_graph_build():
    graph = build_repetition_detector_graph(["S_ZZI", "S_IZZ"], n_rounds=3, measurement_error_probability=0.05)
    assert len(graph.nodes) == 6
    assert len(graph.edges) > 0

def test_syndrome_history_to_events():
    records = [
        Record(0, {"S_ZZI": 0, "S_IZZ": 0}),
        Record(1, {"S_ZZI": 1, "S_IZZ": 0}),
        Record(2, {"S_ZZI": 1, "S_IZZ": 1}),
    ]
    events = syndrome_history_to_detector_events(records)
    assert len(events) == 2

def test_greedy_matching():
    graph = build_repetition_detector_graph(["S_ZZI", "S_IZZ"], n_rounds=3)
    events = [
        DetectorEvent(DetectorNode("S_ZZI@t1", "S_ZZI", 1), 1),
        DetectorEvent(DetectorNode("S_IZZ@t2", "S_IZZ", 2), 1),
    ]
    result = decode_detector_events(graph, events, decoder=GreedyMatchingDecoder())
    assert len(result.matched_pairs) == 1
    assert result.correction == "I"

def test_detector_pipeline():
    result = run_endvqs_detector_graph_pipeline(shots=64, repeats=1, n_rounds=3, n_trials=3, seed=1)
    assert result.circuit_pipeline_result.M.shape == (2, 2)
    assert len(result.detector_graph.nodes) == 6

if __name__ == "__main__":
    test_detector_graph_build()
    test_syndrome_history_to_events()
    test_greedy_matching()
    test_detector_pipeline()
    print("All v1.8 detector graph/matching tests passed.")
