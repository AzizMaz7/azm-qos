from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import IBMRuntimeConfig, diagnose_ibm_runtime, list_ibm_backends, select_least_busy_backend

print("AZM-QOS v2.3 IBM Backend Selection Demo")
print("=" * 70)

config = IBMRuntimeConfig()
diagnostics = diagnose_ibm_runtime(config)
print(diagnostics.summary())
print()

if diagnostics.service_constructed:
    try:
        backends = list_ibm_backends(config, min_qubits=2, include_simulators=False)
        print("Visible backends:")
        for backend in backends[:10]:
            print(" ", backend.summary())
        selected = select_least_busy_backend(config, min_qubits=2)
        print()
        print("Selected backend:", selected.summary())
    except Exception as exc:
        print("Backend listing skipped:", exc)
else:
    print("No IBM Runtime service available; backend selection skipped.")
