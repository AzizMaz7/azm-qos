from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    run_matching_decoder_benchmark,
    export_matching_benchmark_csv,
    make_matching_benchmark_report,
)

print("AZM-QOS v1.9 Matching Decoder Benchmark Demo")
print("=" * 70)

result = run_matching_decoder_benchmark(
    probabilities=[0.0, 0.01, 0.05, 0.10],
    n_trials=30,
    n_rounds=5,
    seed=123,
)

print(result.summary())

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
csv_path = out_dir / "matching_benchmark.csv"
report_path = out_dir / "matching_benchmark_report.md"

export_matching_benchmark_csv(result, csv_path)
make_matching_benchmark_report(result, report_path)

print()
print("Saved CSV:", csv_path)
print("Saved report:", report_path)
