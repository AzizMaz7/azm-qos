from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_mock_sync_workflow

print("AZM-QOS v2.9 Sync Dashboard Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "sync_dashboard_demo"
summary = run_mock_sync_workflow(out_dir)

print(summary.summary())
print()
print("Dashboard artifacts:")
for key, value in summary.dashboard_artifacts.items():
    if "dashboard" in key or "report" in key or "manifest" in key:
        print(f"  {key}: {value}")
