from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_qec_decoder_demo

print("AZM-QOS v4.2 QEC Decoder Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "qec_decoder_demo"
result = run_qec_decoder_demo(out_dir)

print(result.summary())
print()
for estimate in result.decoded_estimates:
    print(estimate.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
