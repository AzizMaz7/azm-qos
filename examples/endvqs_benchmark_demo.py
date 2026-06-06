from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_endvqs import run_endvqs_benchmark, make_endvqs_report

print("AZM-QOS v0.8 END/VQS Benchmark Demo")
print("=" * 70)

data = run_endvqs_benchmark(shots=4096, repeats=25, seed=321)

print("M matrix:")
print(data["M"])
print()
print("V vector:")
print(data["V"])

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
report_path = out_dir / "endvqs_v08_report.md"
make_endvqs_report(data, report_path)

print()
print("Saved report:", report_path)
