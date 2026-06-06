from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    build_repetition_detector_graph,
    detector_graph_to_error_model,
    save_detector_error_model_text,
    save_detector_error_model_json,
    make_detector_error_model_report,
)

print("AZM-QOS v1.9 Detector Error Model Export Demo")
print("=" * 70)

graph = build_repetition_detector_graph(["S_ZZI", "S_IZZ"], n_rounds=5, measurement_error_probability=0.05)
model = detector_graph_to_error_model(graph, default_probability=0.05, logical_labels={"0": "logical_failure_placeholder"})

print(model.summary())
print()
print(model.to_text()[:1200])

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
text_path = out_dir / "detector_error_model.dem.txt"
json_path = out_dir / "detector_error_model.json"
report_path = out_dir / "detector_error_model_report.md"

save_detector_error_model_text(model, text_path)
save_detector_error_model_json(model, json_path)
make_detector_error_model_report(model, graph=graph, output_path=report_path)

print()
print("Saved text:", text_path)
print("Saved JSON:", json_path)
print("Saved report:", report_path)
