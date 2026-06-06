from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    get_code_by_name,
    make_repeated_syndrome_schedule,
)

print("AZM-QOS v4.3 FT Syndrome Circuit Demo")
print("=" * 70)

code = get_code_by_name("repetition3")
schedule = make_repeated_syndrome_schedule(code, rounds=3)

print(code.summary())
print()
for spec in schedule:
    print(spec.summary())
