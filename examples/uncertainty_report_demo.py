from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_mock_uncertainty_workflow

print("AZM-QOS v2.6 Uncertainty Report Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "uncertainty_report_demo"
result = run_mock_uncertainty_workflow(
    output_dir=out_dir,
    n_bootstrap=500,
    confidence_level=0.95,
    seed=123,
)

print(result.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
