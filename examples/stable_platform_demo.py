from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import ensure_production_config

print("AZM-QOS v4.0 Stable Platform Init Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "stable_platform_demo"
config_path, created = ensure_production_config(out_dir / "production_project", project_name="demo_stable_project")

print("Config path:", config_path)
print("Created:", created)
print()
print("Equivalent CLI command:")
print(r"azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project")
