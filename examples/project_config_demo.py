from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import init_project, load_project_config, validate_project_config

print("AZM-QOS v3.0 Project Config Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "project_config_demo"
config, artifacts = init_project(out_dir, project_name="demo_azmqos_project")

print(config.summary())
print()
print("Artifacts:")
for key, value in artifacts.items():
    print(f"  {key}: {value}")

loaded = load_project_config(artifacts["config_path"])
print()
print("Loaded:")
print(loaded.summary())
print("Validation:", validate_project_config(loaded))
