from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_endvqs import default_endvqs_registry
from azmqos_logical import repetition_code_block_encoding, estimate_logical_mapping_resources

print("AZM-QOS v1.2 Logical Resource Demo")
print("=" * 70)

registry = default_endvqs_registry()
encoding = repetition_code_block_encoding(block_size=3)
estimate = estimate_logical_mapping_resources(registry, encoding, shots_per_term=4096, rounds=10)

print(estimate.summary())
print("Notes:", estimate.notes)
