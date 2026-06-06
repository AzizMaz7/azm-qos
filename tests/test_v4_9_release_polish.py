from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    make_clean_command_table,
    make_windows_troubleshooting_guide,
    run_minimal_package_demo,
    run_release_demo,
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_release,
)
from azmqos_research.cli import main

def test_guides_and_minimal_package():
    out_dir = ROOT / "outputs" / "test_v4_9_guides"
    table = make_clean_command_table(out_dir / "command_table.md")
    guide = make_windows_troubleshooting_guide(out_dir / "windows.md")
    archive, manifest = run_minimal_package_demo(out_dir / "minimal")
    assert table.exists()
    assert guide.exists()
    assert archive.exists()
    assert manifest.exists()
    assert "production-init" in table.read_text(encoding="utf-8")

def test_release_demo():
    out_dir = ROOT / "outputs" / "test_v4_9_release_demo"
    result = run_release_demo(out_dir)
    assert Path(result.artifacts["release_manifest"]).exists()
    assert Path(result.artifacts["html_final_report"]).exists()
    assert Path(result.artifacts["minimal_clean_package"]).exists()

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_production_release():
    spec, artifacts = _prepared_spec("test_v4_9_production_release")
    result = run_production_release(
        artifacts["config_path"],
        backend_name="ibm_fez",
        code_name="repetition3",
        max_components=1,
        shots=32,
        rounds=1,
    )
    assert Path(result.artifacts["release_manifest"]).exists()
    assert Path(result.artifacts["html_final_report"]).exists()
    assert Path(result.artifacts["minimal_clean_package"]).exists()

def test_cli_release_commands():
    out_dir = ROOT / "outputs" / "test_v4_9_cli_release_demo"
    code = main(["release-demo", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "production_project" / "release_v4_9" / "release_manifest.json").exists()

    min_out = ROOT / "outputs" / "test_v4_9_cli_minimal"
    code = main(["release-minimal-package", "--output-dir", str(min_out)])
    assert code == 0
    assert (min_out / "minimal_package_demo_manifest.json").exists()

    spec, artifacts = _prepared_spec("test_v4_9_cli_production_release")
    code = main([
        "production-release-run",
        "--config", artifacts["config_path"],
        "--backend-name", "ibm_fez",
        "--code", "repetition3",
        "--max-components", "1",
        "--shots", "32",
        "--rounds", "1",
    ])
    assert code == 0
    assert (Path(spec.output_dir) / "release_v4_9" / "release_manifest.json").exists()

if __name__ == "__main__":
    test_guides_and_minimal_package()
    test_release_demo()
    test_production_release()
    test_cli_release_commands()
    print("All v4.9 release polish tests passed.")
