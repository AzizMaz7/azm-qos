from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import repetition_code_3, default_logical_observables, estimate_qec_resources

print("AZM-QOS v0.9 QEC Resource Demo")
print("=" * 70)

code = repetition_code_3()
logicals = default_logical_observables(code.name)
estimate = estimate_qec_resources(code, logicals=logicals, shots_per_circuit=4096, rounds=3)

print(code.summary())
print()
print(logicals.summary())
print()
print(estimate.summary())
print("Notes:", estimate.notes)
