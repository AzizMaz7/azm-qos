from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import counts_uncertainty

print("AZM-QOS v2.6 Counts Uncertainty Demo")
print("=" * 70)

counts = {"00": 470, "01": 30, "10": 34, "11": 490}
result = counts_uncertainty(counts, confidence_level=0.95)

print(result.summary())
