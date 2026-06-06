from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    init_production_project,
    load_production_spec,
    make_production_plan,
    export_production_plan_json,
    export_production_plan_csv,
    make_production_plan_report,
)

print("AZM-QOS v3.1 Production Plan Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "production_plan_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_plan_project")

spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")

plan = make_production_plan(spec)

plan_dir = out_dir / "plans"
json_path = export_production_plan_json(plan, plan_dir / "production_plan.json")
csv_path = export_production_plan_csv(plan, plan_dir / "production_plan.csv")
report_path = make_production_plan_report(plan, plan_dir / "production_plan_report.md")

print(plan.summary())
print("JSON:", json_path)
print("CSV:", csv_path)
print("Report:", report_path)
