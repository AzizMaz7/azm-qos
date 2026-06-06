from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import run_noise_aware_endvqs_qec_pipeline

print("AZM-QOS v1.5 Noise-Aware END/VQS + QEC Demo")
print("=" * 70)

result = run_noise_aware_endvqs_qec_pipeline(
    shots=256,
    repeats=2,
    syndrome_rounds=5,
    benchmark_trials=20,
    probabilities=[0.0, 0.05, 0.10],
    seed=99,
)

print(result.summary())
print()
print("Decoder benchmark:")
print(result.decoder_benchmark_result.summary())
