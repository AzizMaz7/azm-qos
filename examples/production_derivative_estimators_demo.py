from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    init_production_project,
    load_production_spec,
    save_production_spec,
    run_production_derivative_estimators,
)

print("AZM-QOS v3.8 Production Derivative Estimators Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "production_derivative_estimators_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_derivatives")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, artifacts["config_path"])

result = run_production_derivative_estimators(
    artifacts["config_path"],
    backend="fallback",
    max_components=2,
    shots=128,
)

print(result.summary())
print()
for estimate in result.component_derivatives:
    print(estimate.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
