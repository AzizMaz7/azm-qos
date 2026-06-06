from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_mock_mitigation_workflow

print("AZM-QOS v2.5 Mitigated Hardware Comparison Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "mitigated_hardware_comparison_demo"
result = run_mock_mitigation_workflow(out_dir)

print(result.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
