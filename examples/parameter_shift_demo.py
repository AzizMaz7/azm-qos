from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_derivative_demo

print("AZM-QOS v3.8 Parameter-Shift Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "parameter_shift_demo"
result = run_derivative_demo(out_dir)

print(result.summary())
print()
for estimate in result.component_derivatives:
    print(estimate.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
