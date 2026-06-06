from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    repetition_code_3,
    default_circuit_noise_spec,
    run_circuit_level_syndrome_benchmark,
)

print("AZM-QOS v1.7 Circuit-Level Syndrome Benchmark Demo")
print("=" * 70)

result = run_circuit_level_syndrome_benchmark(
    code_spec=repetition_code_3(),
    noise_spec=default_circuit_noise_spec(),
    n_rounds=5,
    shots=256,
    seed=123,
    use_qiskit_if_available=True,
)

print(result.summary())
print()
for record in result.rounds:
    print(record.summary())
    print()
