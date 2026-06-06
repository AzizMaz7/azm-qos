from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    FinalFigureRecord,
    make_latex_manuscript_scaffold,
    make_thesis_appendix_scaffold,
    make_final_command_summary,
    run_final_export_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_final_export,
)
from azmqos_research.cli import main

def test_scaffolds():
    out_dir = ROOT / "outputs" / "test_v4_8_scaffolds"
    fig = FinalFigureRecord("fig_test", "Test", "figures/test.png", caption="Test caption.")
    manuscript = make_latex_manuscript_scaffold("test_project", [fig], out_dir / "manuscript.tex")
    appendix = make_thesis_appendix_scaffold("test_project", {"manuscript": str(manuscript)}, out_dir / "appendix.md")
    commands = make_final_command_summary(out_dir / "commands.md")
    assert manuscript.exists()
    assert appendix.exists()
    assert commands.exists()
    assert "production-init" in commands.read_text(encoding="utf-8")

def test_final_export_demo():
    out_dir = ROOT / "outputs" / "test_v4_8_final_demo"
    result = run_final_export_demo(out_dir)
    assert len(result.figures) >= 1
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["latex_manuscript"]).exists()
    assert Path(result.artifacts["final_export_archive"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_final_export():
    spec, artifacts = _prepared_spec("test_v4_8_production_final")
    result = run_production_final_export(
        artifacts["config_path"],
        backend_name="ibm_fez",
        code_name="repetition3",
        max_components=1,
        shots=32,
        rounds=1,
    )
    assert len(result.figures) >= 1
    assert Path(result.artifacts["manifest"]).exists()
    assert Path(result.artifacts["latex_manuscript"]).exists()
    assert Path(result.artifacts["final_export_archive"]).exists()

def test_cli_final_export_commands():
    out_dir = ROOT / "outputs" / "test_v4_8_cli_final_demo"
    code = main(["final-export-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "final_export" / "final_export_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_8_cli_production_final")
    code = main([
        "production-final-export",
        "--config", artifacts["config_path"],
        "--backend-name", "ibm_fez",
        "--code", "repetition3",
        "--max-components", "1",
        "--shots", "32",
        "--rounds", "1",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "final_export" / "final_export_manifest.json").exists()

if __name__ == "__main__":
    test_scaffolds()
    test_final_export_demo()
    test_production_final_export()
    test_cli_final_export_commands()
    print("All v4.8 final manuscript/export tests passed.")
