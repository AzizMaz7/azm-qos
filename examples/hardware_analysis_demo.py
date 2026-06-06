from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_hardware_analysis_demo

print("AZM-QOS v4.7 Hardware Analysis Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "hardware_analysis_demo"
result = run_hardware_analysis_demo(out_dir, backend_name="ibm_fez", rounds=2, shots=64)

print(result.summary())
print()
print(result.run_summary.summary())
print()
for item in result.failure_bands:
    print(item.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
