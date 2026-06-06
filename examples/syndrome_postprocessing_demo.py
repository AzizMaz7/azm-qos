from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    default_repetition_code,
    simulate_syndrome_samples,
    decode_syndrome_samples,
    repetition_lookup_table,
)

print("AZM-QOS v4.2 Syndrome Post-Processing Demo")
print("=" * 70)

code = default_repetition_code(3)
samples = simulate_syndrome_samples("demo_component", code, shots=16, physical_error_rate=0.15)
decoded = decode_syndrome_samples(samples, code)

print(code.summary())
print("Lookup table:", repetition_lookup_table(3))
print()
for sample, result in zip(samples[:8], decoded[:8]):
    print(sample.summary())
    print(result.summary())
    print()
