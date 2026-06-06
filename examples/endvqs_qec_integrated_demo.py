from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_pipeline import (
    ResearchPipelineConfig,
    run_integrated_research_pipeline,
    make_integrated_markdown_report,
)

print("AZM-QOS v1.0 END/VQS + QEC Integrated Demo")
print("=" * 70)

config = ResearchPipelineConfig(
    backend_policy="shot_simulator",
    shots=4096,
    repeats=25,
    seed=321,
    qec_code="repetition3",
    output_label="endvqs_qec_integrated_demo",
)

result = run_integrated_research_pipeline(config)

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
report_path = out_dir / "integrated_pipeline_report.md"
make_integrated_markdown_report(result, report_path)

print(result.summary())
print()
print("Saved integrated report:", report_path)
