from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import init_production_project, load_production_spec, save_production_spec, run_production_shot_scaling
print("AZM-QOS v3.3 Production Shot-Scaling Demo")
print("=" * 70)
out_dir = ROOT / "outputs" / "production_shot_scaling_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_shot_scaling")
spec = load_production_spec(artifacts["config_path"])
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, artifacts["config_path"])
result = run_production_shot_scaling(artifacts["config_path"], shot_powers=(6, 8, 10), backend="fallback")
print("Points:", len(result["points"]))
for point in result["points"][:8]:
    print(point.summary())
print("CSV:", result["csv"])
print("Figure:", result["figure"])
print("Manifest:", result["manifest"])
