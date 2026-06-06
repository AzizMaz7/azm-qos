from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_pipeline import (
    ResearchPipelineConfig,
    run_integrated_research_pipeline,
    make_manuscript_style_report,
)

print("AZM-QOS v1.0 Manuscript Report Demo")
print("=" * 70)

config = ResearchPipelineConfig(
    backend_policy="shot_simulator",
    shots=4096,
    repeats=25,
    seed=99,
    qec_code="repetition3",
    output_label="manuscript_demo",
)

result = run_integrated_research_pipeline(config)

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
report_path = out_dir / "manuscript_style_report.md"
text = make_manuscript_style_report(result, report_path)

print(text[:1200])
print()
print("Saved manuscript-style report:", report_path)
