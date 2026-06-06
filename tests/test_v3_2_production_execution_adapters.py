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
    make_production_plan,
    production_plan_to_workloads,
    make_job_manifest,
    run_simulator_batch,
    run_hardware_dry_run_batch,
    run_production_execution_adapter,
)
from azmqos_research.cli import main

def _prepared_spec(tmp_name):
    out_dir = ROOT / "outputs" / tmp_name
    spec, artifacts = init_production_project(out_dir, project_name=tmp_name)
    spec = load_production_spec(artifacts["config_path"])
    spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
    save_production_spec(spec, artifacts["config_path"])
    return spec, artifacts

def test_workload_conversion():
    spec, artifacts = _prepared_spec("test_v3_2_workload_conversion")
    plan = make_production_plan(spec)
    workloads = production_plan_to_workloads(plan, spec)
    assert len(workloads) == len(plan.items)
    assert workloads[0].measurement_type in ["metric_matrix_element", "gradient_vector_element"]

def test_job_manifest():
    spec, artifacts = _prepared_spec("test_v3_2_manifest")
    plan = make_production_plan(spec)
    workloads = production_plan_to_workloads(plan, spec)
    manifest = make_job_manifest(spec, workloads)
    assert len(manifest.workloads) == len(workloads)
    assert manifest.dry_run is True

def test_simulator_batch():
    spec, artifacts = _prepared_spec("test_v3_2_sim_batch")
    plan = make_production_plan(spec)
    workloads = production_plan_to_workloads(plan, spec)
    results = run_simulator_batch(workloads)
    assert len(results) == len(workloads)
    assert all(r.status == "completed" for r in results)
    assert all(r.counts is not None for r in results)

def test_hardware_dry_run_batch():
    spec, artifacts = _prepared_spec("test_v3_2_hw_dry_batch")
    spec.execution_policy.mode = "hardware_dry_run"
    plan = make_production_plan(spec)
    workloads = production_plan_to_workloads(plan, spec)
    results = run_hardware_dry_run_batch(workloads)
    assert len(results) == len(workloads)
    assert all(r.status == "dry_run_prepared" for r in results)
    assert all((r.job_id or "").startswith("DRYRUN-") for r in results)

def test_production_execution_adapter():
    spec, artifacts = _prepared_spec("test_v3_2_adapter")
    result = run_production_execution_adapter(artifacts["config_path"])
    assert len(result.results) == len(result.workloads)
    assert Path(result.artifacts["production_execution_manifest"]).exists()
    assert Path(result.artifacts["dashboard_html"]).exists()

def test_cli_production_execute():
    spec, artifacts = _prepared_spec("test_v3_2_cli_execute")
    code = main(["production-execute", "--config", artifacts["config_path"], "--mode", "simulator"])
    assert code == 0
    assert (Path(spec.output_dir) / "execution" / "production_execution_manifest.json").exists()

if __name__ == "__main__":
    test_workload_conversion()
    test_job_manifest()
    test_simulator_batch()
    test_hardware_dry_run_batch()
    test_production_execution_adapter()
    test_cli_production_execute()
    print("All v3.2 production execution adapter tests passed.")
