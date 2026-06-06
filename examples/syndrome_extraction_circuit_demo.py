from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import repetition_code_3, build_syndrome_extraction_specs_for_code

print("AZM-QOS v1.3 Syndrome-Extraction Circuit Demo")
print("=" * 70)

code = repetition_code_3()
specs = build_syndrome_extraction_specs_for_code(code)

print(code.summary())
print()

for spec in specs:
    print(spec.summary())
    print()

try:
    from azmqos_qec import syndrome_spec_to_qiskit
    qc = syndrome_spec_to_qiskit(specs[0])
    print("Qiskit circuit for first stabilizer:")
    print(qc)
except Exception as exc:
    print("Qiskit circuit generation skipped:", exc)
