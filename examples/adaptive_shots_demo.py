from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import (
    make_chemistry_style_h2_proxy_workload,
    uniform_shot_allocation,
    coefficient_weighted_shot_allocation,
    variance_aware_shot_allocation,
)

workload = make_chemistry_style_h2_proxy_workload(theta=0.6)
total_shots = 10000

print("AZM-QOS v0.5 Adaptive Shot Allocation Demo")
print("=" * 70)

for allocator in [
    uniform_shot_allocation,
    coefficient_weighted_shot_allocation,
    variance_aware_shot_allocation,
]:
    allocation = allocator(workload, total_shots)
    print()
    print(allocation.summary())
