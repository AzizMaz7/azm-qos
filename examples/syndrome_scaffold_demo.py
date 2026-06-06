from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import default_repetition_code, default_five_qubit_code, make_syndrome_specs

print("AZM-QOS v4.1 Syndrome Scaffold Demo")
print("=" * 70)

for code in [default_repetition_code(3), default_five_qubit_code()]:
    print(code.summary())
    for spec in make_syndrome_specs(code):
        print(spec.summary())
    print()
