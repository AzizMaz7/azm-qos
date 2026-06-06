from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    build_repetition_detector_graph,
    DetectorNode,
    DetectorEvent,
    decode_detector_events,
    GreedyMatchingDecoder,
    pymatching_available,
)

print("AZM-QOS v1.8 Matching Decoder Demo")
print("=" * 70)

graph = build_repetition_detector_graph(["S_ZZI", "S_IZZ"], n_rounds=4, measurement_error_probability=0.05)

events = [
    DetectorEvent(DetectorNode("S_ZZI@t1", "S_ZZI", 1), 1),
    DetectorEvent(DetectorNode("S_IZZ@t2", "S_IZZ", 2), 1),
]

result = decode_detector_events(graph, events, decoder=GreedyMatchingDecoder())

print(graph.summary())
print("PyMatching available:", pymatching_available())
print(result.summary())
print("Pairs:", result.matched_pairs)
print("Unmatched:", result.unmatched_events)
