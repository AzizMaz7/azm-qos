from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    synthetic_noise_scaled_derivatives,
    linear_zne_extrapolate,
    ZNEConfig,
)

print("AZM-QOS v3.9 ZNE Derivative Demo")
print("=" * 70)

raw_derivative = 0.125
config = ZNEConfig(noise_factors=[1.0, 3.0, 5.0])
points = synthetic_noise_scaled_derivatives(raw_derivative, config.noise_factors)
zne = linear_zne_extrapolate(points)

print("Raw derivative:", raw_derivative)
print("Noise-scaled points:", points)
print("ZNE extrapolated derivative:", zne)
