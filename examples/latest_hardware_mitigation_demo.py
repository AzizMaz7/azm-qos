from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_latest_hardware_mitigation_workflow

print("AZM-QOS v2.5 Latest Hardware Mitigation Demo")
print("=" * 70)

# Replace with simulator counts for the same circuit/job.
simulator_counts = {"00": 510, "11": 514}

# backend_name=None means latest visible job from any backend.
# Use backend_name="ibm_fez" to restrict.
out_dir = ROOT / "outputs" / "latest_hardware_mitigation_demo"

result = run_latest_hardware_mitigation_workflow(
    output_dir=out_dir,
    simulator_counts=simulator_counts,
    backend_name=None,
)

print(result.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
