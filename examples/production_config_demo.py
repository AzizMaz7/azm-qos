from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import init_production_project, load_production_spec, validate_production_spec

print("AZM-QOS v3.1 Production Config Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "production_config_demo"
spec, artifacts = init_production_project(out_dir, project_name="demo_endvqs_production")

print(spec.summary())
print()
print("Artifacts:")
for key, value in artifacts.items():
    print(f"  {key}: {value}")

loaded = load_production_spec(artifacts["config_path"])
print()
print("Loaded:")
print(loaded.summary())
print("Validation:", validate_production_spec(loaded))
