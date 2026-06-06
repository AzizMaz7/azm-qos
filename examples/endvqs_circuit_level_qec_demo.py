from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_pipeline import run_endvqs_circuit_level_qec_pipeline

print("AZM-QOS v1.7 END/VQS + Circuit-Level QEC Demo")
print("=" * 70)

result = run_endvqs_circuit_level_qec_pipeline(
    shots=128,
    repeats=1,
    n_rounds=3,
    n_trials=5,
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
print("Circuit-level decoder sweep:")
print(result.circuit_decoder_sweep_result.summary())
