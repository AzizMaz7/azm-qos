from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_mock_sync_workflow

print("AZM-QOS v2.9 Job Synchronization Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "job_sync_demo"
summary = run_mock_sync_workflow(out_dir)

print(summary.summary())
print()
print("Results:")
for result in summary.results:
    print(result.summary())
    print()
print("Artifacts:")
for key, value in summary.dashboard_artifacts.items():
    print(f"  {key}: {value}")
