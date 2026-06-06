from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    get_code_by_name,
    default_backend_target,
    CircuitNoiseModel,
    recommend_noise_aware_layout,
)

print("AZM-QOS v4.4 QEC Layout Recommendation Demo")
print("=" * 70)

code = get_code_by_name("repetition3")
backend = default_backend_target("ibm_fez")
noise = CircuitNoiseModel(data_error_rate=0.02, measurement_error_rate=0.03)
layout = recommend_noise_aware_layout(code, backend, noise)

print(code.summary())
print()
print(backend.summary())
print()
print(noise.summary())
print()
print(layout.summary())
