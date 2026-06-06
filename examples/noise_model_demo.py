from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    get_code_by_name,
    CircuitNoiseModel,
    effective_round_error_probability,
    simulate_repeated_syndrome_rounds,
)

print("AZM-QOS v4.3 Noise Model Demo")
print("=" * 70)

code = get_code_by_name("repetition3")
noise = CircuitNoiseModel(data_error_rate=0.02, measurement_error_rate=0.03)

print(noise.summary())
print("Effective round error probability:", effective_round_error_probability(noise, code))
print()

rounds = simulate_repeated_syndrome_rounds("demo_component", code, rounds=5, noise=noise)
for item in rounds:
    print(item.summary())
