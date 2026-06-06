from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import init_production_project, load_production_spec, save_production_spec, make_production_plan, production_plan_to_workloads, workload_to_circuit_spec, exact_expectation_from_circuit_spec
print("AZM-QOS v3.3 Workload-to-Circuit Demo")
print("=" * 70)
out_dir = ROOT / "outputs" / "workload_to_circuit_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_workload_to_circuit")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, artifacts["config_path"])
plan = make_production_plan(spec)
workloads = production_plan_to_workloads(plan, spec)
for workload in workloads:
    circuit = workload_to_circuit_spec(workload)
    print(workload.summary())
    print(circuit.summary())
    print("Exact expectation:", exact_expectation_from_circuit_spec(circuit))
    print()
