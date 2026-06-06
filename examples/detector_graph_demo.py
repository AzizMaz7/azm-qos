from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    build_repetition_detector_graph,
    save_detector_graph_json,
    make_detector_graph_report,
)

print("AZM-QOS v1.8 Detector Graph Demo")
print("=" * 70)

graph = build_repetition_detector_graph(["S_ZZI", "S_IZZ"], n_rounds=5, measurement_error_probability=0.05)
print(graph.summary())

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
json_path = out_dir / "detector_graph.json"
report_path = out_dir / "detector_graph_report.md"

save_detector_graph_json(graph, json_path)
make_detector_graph_report(graph, output_path=report_path)

print("Saved graph JSON:", json_path)
print("Saved graph report:", report_path)
