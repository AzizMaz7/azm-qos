from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import (
    RuntimeManager,
    BackendSelector,
    BackendSelectionRequest,
    make_generic_two_qubit_workload,
)

workload = make_generic_two_qubit_workload()
manager = RuntimeManager()
selector = BackendSelector()

requests = [
    BackendSelectionRequest(require_exact=True),
    BackendSelectionRequest(require_shots=True),
    BackendSelectionRequest(allow_cloud=True, prefer_hardware=True),
]

print("AZM-QOS v0.7 Backend Selection Demo")
print("=" * 70)

for req in requests:
    selection = selector.select(manager, workload, req)
    print()
    print("Request:", req)
    print("Selected backend:", selection.backend_name)
    print("Reason:", selection.reason)
    if selection.metadata:
        print("Metadata:", selection.metadata)
