from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import create_demo_run_database, export_dashboard_json

print("AZM-QOS v2.7 Dashboard Export Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "dashboard_export_demo"
db, records, artifacts = create_demo_run_database(out_dir)

dashboard = export_dashboard_json(records, out_dir / "dashboard_export.json")

print("Records:", len(records))
print("Dashboard:", dashboard)
print("Existing artifacts:")
for key, value in artifacts.items():
    print(f"  {key}: {value}")
