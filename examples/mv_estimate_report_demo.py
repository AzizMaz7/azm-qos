from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import init_production_project, load_production_spec, save_production_spec, run_production_pauli_execution
print("AZM-QOS v3.5 M/V Estimate Report Demo")
print("=" * 70)
out_dir = ROOT / "outputs" / "mv_estimate_report_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_mv_report")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, artifacts["config_path"])
result = run_production_pauli_execution(artifacts["config_path"], shots_per_group=512)
print("M table:", result.artifacts["M_estimates_csv"])
print("V table:", result.artifacts["V_estimates_csv"])
print("Report:", result.artifacts["mv_estimate_report"])
