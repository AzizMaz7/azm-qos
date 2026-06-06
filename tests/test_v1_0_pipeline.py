from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import (
    ResearchPipelineConfig,
    run_integrated_research_pipeline,
    make_integrated_markdown_report,
    make_manuscript_style_report,
)

def test_pipeline_runs():
    config = ResearchPipelineConfig(shots=128, repeats=2, seed=1)
    result = run_integrated_research_pipeline(config)
    assert result.M.shape == (2, 2)
    assert result.V.shape == (2,)
    assert len(result.endvqs_results) > 0
    assert len(result.qec_results) > 0

def test_reports_create_text():
    config = ResearchPipelineConfig(shots=128, repeats=2, seed=1)
    result = run_integrated_research_pipeline(config)
    report = make_integrated_markdown_report(result)
    manuscript = make_manuscript_style_report(result)
    assert "Integrated Research Pipeline" in report
    assert "Manuscript-Style" in manuscript

if __name__ == "__main__":
    test_pipeline_runs()
    test_reports_create_text()
    print("All v1.0 pipeline tests passed.")
