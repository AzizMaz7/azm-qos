from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import run_decoder_noise_sweep, export_decoder_benchmark_csv, make_decoder_benchmark_report

print("AZM-QOS v1.5 Decoder Benchmark Report Demo")
print("=" * 70)

result = run_decoder_noise_sweep(
    probabilities=[0.0, 0.02, 0.05, 0.10],
    n_trials=20,
    n_rounds=5,
    shots=256,
    seed=7,
)

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
csv_path = out_dir / "decoder_benchmark.csv"
report_path = out_dir / "decoder_benchmark_report.md"

export_decoder_benchmark_csv(result, csv_path)
make_decoder_benchmark_report(result, report_path)

print(result.summary())
print()
print("Saved CSV:", csv_path)
print("Saved report:", report_path)
