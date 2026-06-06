from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_ft_qec,
)

print("AZM-QOS v4.3 Production FT-QEC Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "production_ft_qec_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_ft_qec")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, artifacts["config_path"])

result = run_production_ft_qec(
    artifacts["config_path"],
    code_name="repetition3",
    max_components=2,
    shots=64,
    rounds=3,
    physical_error_rate=0.02,
    measurement_error_rate=0.03,
)

print(result.summary())
print()
for item in result.component_results:
    print(item.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
