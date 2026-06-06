from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_endvqs import default_endvqs_registry
from azmqos_logical import (
    repetition_code_block_encoding,
    encode_term_registry,
    compare_registry_sizes,
    make_logical_mapping_report,
)

print("AZM-QOS v1.2 Logical Mapping Demo")
print("=" * 70)

physical_registry = default_endvqs_registry()
encoding = repetition_code_block_encoding(block_size=3)
logical_registry = encode_term_registry(physical_registry, encoding)

print(encoding.summary())
print()
print("Registry size comparison:")
print(compare_registry_sizes(physical_registry, logical_registry))

out_dir = ROOT / "outputs"
out_dir.mkdir(exist_ok=True)
report_path = out_dir / "logical_mapping_report.md"
make_logical_mapping_report(physical_registry, logical_registry, encoding, report_path)

print()
print("Saved report:", report_path)
