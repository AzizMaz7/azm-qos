from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import (
    repetition_code_3,
    build_syndrome_extraction_specs_for_code,
    default_circuit_noise_spec,
    qiskit_aer_noise_available,
    estimate_noisy_syndrome_probability_scaffold,
)

print("AZM-QOS v1.6 Noisy Syndrome Circuit Demo")
print("=" * 70)

code = repetition_code_3()
spec = build_syndrome_extraction_specs_for_code(code)[0]
noise = default_circuit_noise_spec()

print(spec.summary())
print()
print(noise.summary())

weight = sum(1 for c in spec.stabilizer.pauli if c != "I")
print()
print("Fallback scaffold syndrome p(1):", estimate_noisy_syndrome_probability_scaffold(noise, weight))

if qiskit_aer_noise_available():
    from azmqos_qec import run_noisy_syndrome_circuit_qiskit
    result = run_noisy_syndrome_circuit_qiskit(spec, noise, shots=1024, seed=123)
    print(result.summary())
    print(result.counts)
else:
    print("Qiskit Aer not installed; skipped noisy circuit simulation.")
