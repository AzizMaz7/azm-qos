from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    init_project,
    load_project_config,
    validate_project_config,
    default_plugin_registry,
    save_plugin_registry,
    run_integrated_workflow,
)
from azmqos_research.cli import main

def test_project_init_and_load():
    out_dir = ROOT / "outputs" / "test_v3_0_project_init"
    config, artifacts = init_project(out_dir, project_name="test_project")
    assert Path(artifacts["config_path"]).exists()
    loaded = load_project_config(artifacts["config_path"])
    assert loaded.project_name == "test_project"
    assert validate_project_config(loaded) == []

def test_plugin_registry():
    out_dir = ROOT / "outputs" / "test_v3_0_registry"
    out_dir.mkdir(parents=True, exist_ok=True)
    registry = default_plugin_registry()
    path = save_plugin_registry(registry, out_dir / "registry.json")
    assert Path(path).exists()
    assert len(registry.plugins) >= 3

def test_integrated_workflow():
    out_dir = ROOT / "outputs" / "test_v3_0_integrated"
    config, artifacts = init_project(out_dir, project_name="integrated_test")
    result = run_integrated_workflow(artifacts["config_path"])
    assert "final_archive" in result.artifacts
    assert Path(result.artifacts["final_archive"]).exists()
    assert "dashboard_html" in result.artifacts
    assert "project_summary_report" in result.artifacts

def test_cli_app_commands():
    out_dir = ROOT / "outputs" / "test_v3_0_cli_project"
    code = main(["app-init", "--output-dir", str(out_dir), "--project-name", "cli_project"])
    assert code == 0
    config_path = out_dir / "azmqos_project.json"
    assert config_path.exists()

    code = main(["app-report", "--config", str(config_path)])
    assert code == 0

    code = main(["app-run", "--config", str(config_path)])
    assert code == 0
    assert (out_dir / "archives" / "cli_project_azmqos_archive.zip").exists()

if __name__ == "__main__":
    test_project_init_and_load()
    test_plugin_registry()
    test_integrated_workflow()
    test_cli_app_commands()
    print("All v3.0 integrated research app tests passed.")
