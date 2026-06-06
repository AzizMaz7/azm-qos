from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_qec_hardware_dry_run,
)

print("AZM-QOS v4.4 Production QEC Hardware Dry-Run Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "production_qec_hardware_dry_run_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_qec_hardware")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, artifacts["config_path"])

result = run_production_qec_hardware_dry_run(
    artifacts["config_path"],
    backend_name="ibm_fez",
    code_name="repetition3",
    max_components=2,
    shots=64,
    rounds=3,
)

print(result.summary())
print()
for item in result.job_manifests:
    print(item.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
