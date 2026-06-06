from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    load_registry_for_research,
    export_term_audit_csv,
    run_real_term_research_pipeline,
)
from azmqos_research.cli import main

def test_load_component_registry_template():
    template = ROOT / "templates" / "endvqs_real_terms_template.json"
    result = load_registry_for_research(component_registry_json=template)
    assert result.validation.ok
    assert result.registry.dimension == 2

def test_term_audit_export():
    template = ROOT / "templates" / "endvqs_real_terms_template.json"
    result = load_registry_for_research(component_registry_json=template)
    out = ROOT / "outputs" / "test_v2_1_term_audit.csv"
    out.parent.mkdir(exist_ok=True)
    export_term_audit_csv(result.registry, out)
    assert out.exists()

def test_real_term_pipeline_runs():
    template = ROOT / "templates" / "endvqs_real_terms_template.json"
    out_dir = ROOT / "outputs" / "test_v2_1_real_term_pipeline"
    result = run_real_term_research_pipeline(
        output_dir=out_dir,
        component_registry_json=template,
        shots=64,
        repeats=1,
        n_rounds=3,
        n_trials=5,
        seed=1,
    )
    assert result.M.shape == (2, 2)
    assert result.V.shape == (2,)
    assert "term_audit_csv" in result.artifacts
    assert Path(result.artifacts["reproducibility_bundle"]).exists()

def test_real_term_cli_runs():
    template = ROOT / "templates" / "endvqs_real_terms_template.json"
    out_dir = ROOT / "outputs" / "test_v2_1_cli"
    code = main([
        "real-terms",
        "--component-registry", str(template),
        "--output-dir", str(out_dir),
        "--shots", "64",
        "--repeats", "1",
        "--rounds", "3",
        "--trials", "5",
    ])
    assert code == 0
    assert (out_dir / "experiment_manifest.json").exists()

if __name__ == "__main__":
    test_load_component_registry_template()
    test_term_audit_export()
    test_real_term_pipeline_runs()
    test_real_term_cli_runs()
    print("All v2.1 real-terms workflow tests passed.")
