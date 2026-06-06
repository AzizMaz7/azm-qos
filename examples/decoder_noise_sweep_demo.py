from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import run_decoder_noise_sweep

print("AZM-QOS v1.5 Decoder Noise Sweep Demo")
print("=" * 70)

result = run_decoder_noise_sweep(
    probabilities=[0.0, 0.02, 0.05, 0.10, 0.15],
    n_trials=30,
    n_rounds=5,
    shots=256,
    seed=123,
)

print(result.summary())
