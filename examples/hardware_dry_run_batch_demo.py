from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_execution_adapter,
)

print("AZM-QOS v3.2 Hardware Dry-Run Batch Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "hardware_dry_run_batch_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_hardware_dry_run")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
spec.execution_policy.mode = "hardware_dry_run"
spec.execution_policy.backend_name = "ibm_fez"
save_production_spec(spec, artifacts["config_path"])

result = run_production_execution_adapter(artifacts["config_path"])

print(result.summary())
print()
for item in result.results:
    print(item.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
