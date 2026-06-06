from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_qec_hardware_sync_demo

print("AZM-QOS v4.5 Hardware Job Sync Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "hardware_job_sync_demo"
result = run_qec_hardware_sync_demo(out_dir, backend_name="ibm_fez", rounds=2, shots=64)

print(result.summary())
print()
for item in result.comparisons:
    print(item.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
