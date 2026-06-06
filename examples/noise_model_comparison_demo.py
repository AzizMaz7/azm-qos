from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import compare_circuit_noise_to_syndrome_noise, make_noise_model_comparison_report

print("AZM-QOS v1.6 Noise Model Comparison Demo")
print("=" * 70)

result = compare_circuit_noise_to_syndrome_noise(
    n_trials=10,
    n_rounds=3,
    shots=128,
    seed=123,
)

print(result.summary())

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
report_path = out_dir / "noise_model_comparison_report.md"
make_noise_model_comparison_report(result, report_path)

print()
print("Saved report:", report_path)
