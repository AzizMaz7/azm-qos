from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    ensure_production_config,
    load_production_spec,
    save_production_spec,
    run_stable_workflow,
    run_stable_smoke_test,
)
from azmqos_research.cli import main

def test_ensure_production_config():
    out_dir = ROOT / "outputs" / "test_v4_0_ensure_config"
    config_path, created = ensure_production_config(out_dir, project_name="test_project")
    assert Path(config_path).exists()

def test_stable_workflow():
    out_dir = ROOT / "outputs" / "test_v4_0_stable_workflow"
    config_path, created = ensure_production_config(out_dir / "production_project", project_name="test_stable")
    spec = load_production_spec(config_path)
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, config_path)

    result = run_stable_workflow(config_path, backend="fallback", max_components=1, shots=32)
    assert "stable_manifest" in result.artifacts
    assert Path(result.artifacts["stable_manifest"]).exists()
    assert "stable_archive" in result.artifacts
    assert Path(result.artifacts["stable_archive"]).exists()

def test_stable_smoke_test():
    out_dir = ROOT / "outputs" / "test_v4_0_smoke"
    result = run_stable_smoke_test(out_dir)
    assert Path(result.artifacts["stable_manifest"]).exists()
    assert Path(result.artifacts["stable_archive"]).exists()

def test_cli_stable_commands():
    out_dir = ROOT / "outputs" / "test_v4_0_cli"
    code = main(["stable-smoke-test", "--output-dir", str(out_dir)])
    assert code == 0
    assert (out_dir / "production_project" / "stable_v4_0" / "stable_workflow_manifest.json").exists()

    config_path = out_dir / "production_project" / "azmqos_production.json"
    code = main([
        "stable-run",
        "--config", str(config_path),
        "--backend", "fallback",
        "--max-components", "1",
        "--shots", "32",
    ])
    assert code == 0

if __name__ == "__main__":
    test_ensure_production_config()
    test_stable_workflow()
    test_stable_smoke_test()
    test_cli_stable_commands()
    print("All v4.0 stable integrated platform tests passed.")
