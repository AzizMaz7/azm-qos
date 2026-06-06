from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    init_production_project,
    load_production_spec,
    save_production_spec,
    validate_production_spec,
    make_production_plan,
    export_production_plan_json,
    export_production_plan_csv,
    run_production_dry_run,
)
from azmqos_research.cli import main

def test_init_and_load_production_project():
    out_dir = ROOT / "outputs" / "test_v3_1_init"
    spec, artifacts = init_production_project(out_dir, project_name="test_prod")
    assert Path(artifacts["config_path"]).exists()
    loaded = load_production_spec(artifacts["config_path"])
    assert loaded.project_name == "test_prod"
    assert validate_production_spec(loaded) == []

def test_make_plan_from_template_registry():
    out_dir = ROOT / "outputs" / "test_v3_1_plan"
    spec, artifacts = init_production_project(out_dir, project_name="test_plan")
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    plan = make_production_plan(spec)
    assert len(plan.items) >= 1
    assert any(item.family in ["Mbb", "Mab", "Maa", "Va", "Vb"] for item in plan.items)

def test_plan_exports():
    out_dir = ROOT / "outputs" / "test_v3_1_plan_exports"
    spec, artifacts = init_production_project(out_dir, project_name="test_exports")
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    plan = make_production_plan(spec)
    json_path = export_production_plan_json(plan, out_dir / "plan.json")
    csv_path = export_production_plan_csv(plan, out_dir / "plan.csv")
    assert Path(json_path).exists()
    assert Path(csv_path).exists()

def test_production_dry_run():
    out_dir = ROOT / "outputs" / "test_v3_1_dry_run"
    spec, artifacts = init_production_project(out_dir, project_name="test_dry_run")
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    result = run_production_dry_run(artifacts["config_path"])
    assert len(result.plan.items) >= 1
    assert Path(result.artifacts["production_archive"]).exists()
    assert Path(result.artifacts["dashboard_html"]).exists()

def test_cli_production_commands():
    out_dir = ROOT / "outputs" / "test_v3_1_cli"
    code = main(["production-init", "--output-dir", str(out_dir), "--project-name", "cli_prod"])
    assert code == 0
    config_path = out_dir / "azmqos_production.json"
    assert config_path.exists()

    spec = load_production_spec(config_path)
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, config_path)

    code = main(["production-plan", "--config", str(config_path)])
    assert code == 0
    assert (out_dir / "plans" / "production_plan.json").exists()

    code = main(["production-run", "--config", str(config_path)])
    assert code == 0
    assert (out_dir / "archives" / "cli_prod_production_archive.zip").exists()

if __name__ == "__main__":
    test_init_and_load_production_project()
    test_make_plan_from_template_registry()
    test_plan_exports()
    test_production_dry_run()
    test_cli_production_commands()
    print("All v3.1 END/VQS production config tests passed.")
