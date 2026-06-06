from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_qec import (
    repetition_code_3,
    build_stabilizer_workloads,
    infer_syndrome_from_stabilizers,
    MajorityVoteRepetitionDecoder,
)

print("AZM-QOS v0.9 QEC Syndrome Demo")
print("=" * 70)

code = repetition_code_3()
workloads = build_stabilizer_workloads(code)
manager = RuntimeManager()

results = [manager.run(w, "local_statevector", RuntimeConfig()) for w in workloads]
syndrome = infer_syndrome_from_stabilizers(results)
decoder_result = MajorityVoteRepetitionDecoder().decode(syndrome)

print(syndrome.summary())
print()
print(decoder_result.summary())
