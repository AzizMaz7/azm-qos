from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_derivative_mitigation_demo

print("AZM-QOS v3.9 Derivative Mitigation Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "derivative_mitigation_demo"
result = run_derivative_mitigation_demo(out_dir)

print(result.summary())
print()
for estimate in result.mitigated_derivatives:
    print(estimate.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
