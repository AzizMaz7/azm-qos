from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_qec import repetition_code_3, run_decoder_aware_qec_execution

print("AZM-QOS v1.4 Decoder-Aware Execution Demo")
print("=" * 70)

result = run_decoder_aware_qec_execution(
    code_spec=repetition_code_3(),
    n_rounds=7,
    backend_name="local_statevector",
    shots=1024,
    seed=42,
    measurement_error_probability=0.15,
)

print(result.summary())
