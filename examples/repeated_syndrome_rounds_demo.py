from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import repetition_code_3, run_repeated_syndrome_rounds

print("AZM-QOS v1.4 Repeated Syndrome Rounds Demo")
print("=" * 70)

code = repetition_code_3()
result = run_repeated_syndrome_rounds(
    code,
    n_rounds=5,
    backend_name="local_statevector",
    shots=1024,
    seed=123,
    measurement_error_probability=0.10,
)

print(result.summary())
print()
for record in result.rounds:
    print(record.summary())
    print()
