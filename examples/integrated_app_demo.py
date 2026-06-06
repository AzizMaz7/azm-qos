from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import init_project, run_integrated_workflow

print("AZM-QOS v3.0 Integrated App Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "integrated_app_demo"
config, init_artifacts = init_project(out_dir, project_name="demo_integrated_azmqos")

result = run_integrated_workflow(init_artifacts["config_path"])

print(result.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
