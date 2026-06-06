from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import run_endvqs_logical_decoder_pipeline

print("AZM-QOS v1.4 Encoded END/VQS + Decoder-Aware QEC Demo")
print("=" * 70)

result = run_endvqs_logical_decoder_pipeline(
    shots=512,
    repeats=3,
    syndrome_rounds=5,
    measurement_error_probability=0.10,
    seed=99,
)

print(result.summary())
print()
print("M matrix:")
print(result.M)
print()
print("V vector:")
print(result.V)
print()
print("Decoder-aware QEC summary:")
print(result.decoder_execution_result.summary())
