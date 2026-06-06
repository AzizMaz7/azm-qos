from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    init_production_project,
    load_production_spec,
    save_production_spec,
    make_production_plan,
    production_plan_to_workloads,
    make_job_manifest,
)

print("AZM-QOS v3.2 Production Execution Plan Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "production_execution_plan_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_execution_plan")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, artifacts["config_path"])

plan = make_production_plan(spec)
workloads = production_plan_to_workloads(plan, spec)
manifest = make_job_manifest(spec, workloads)

print(plan.summary())
print()
print(manifest.summary())
print()
for workload in workloads:
    print(workload.summary())
    print()
