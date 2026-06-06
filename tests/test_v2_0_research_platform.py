from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    create_experiment_manifest,
    run_research_platform_pipeline,
    make_latex_research_report,
    make_markdown_research_report,
)
from azmqos_research.cli import main

def test_manifest():
    manifest = create_experiment_manifest("test", {"shots": 64})
    assert manifest.name == "test"
    assert manifest.azmqos_version == "2.0.0"

def test_research_pipeline_runs():
    out_dir = ROOT / "outputs" / "test_v2_0_research_pipeline"
    result = run_research_platform_pipeline(out_dir, shots=64, repeats=1, n_rounds=3, n_trials=5, seed=1)
    assert result.M.shape == (2, 2)
    assert result.V.shape == (2,)
    assert "manifest_json" in result.artifacts
    assert Path(result.artifacts["reproducibility_bundle"]).exists()

def test_cli_runs():
    out_dir = ROOT / "outputs" / "test_v2_0_cli"
    code = main(["run", "--output-dir", str(out_dir), "--shots", "64", "--repeats", "1", "--rounds", "3", "--trials", "5"])
    assert code == 0
    assert (out_dir / "experiment_manifest.json").exists()

if __name__ == "__main__":
    test_manifest()
    test_research_pipeline_runs()
    test_cli_runs()
    print("All v2.0 research platform tests passed.")
