from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    parse_counts_from_runtime_result,
    parse_estimator_value,
    compare_counts,
    compare_expectation_values,
)

print("AZM-QOS v2.4 Hardware Result Parsing Demo")
print("=" * 70)

runtime_like_counts = {"counts": {"00": 470, "01": 30, "10": 34, "11": 490}}
hardware_counts = parse_counts_from_runtime_result(runtime_like_counts)
simulator_counts = {"00": 510, "11": 514}

counts_comparison = compare_counts(simulator_counts, hardware_counts)
expectation = parse_estimator_value({"values": [0.913]})
expectation_comparison = compare_expectation_values(1.0, expectation)

print(counts_comparison.summary())
print()
print(expectation_comparison.summary())
