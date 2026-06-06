from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import RuntimeManager, diagnose_ibm_runtime, ibm_runtime_available

print("AZM-QOS v0.7 IBM Runtime Adapter Demo")
print("=" * 70)

print("qiskit-ibm-runtime available:", ibm_runtime_available())
diag = diagnose_ibm_runtime()
print(diag.summary())

manager = RuntimeManager()
print("\nRegistered backends:")
for name, info in manager.list_backends().items():
    print(f"  {name}: {info.backend_type} | {info.description}")

print("\nNote:")
print("IBMRuntimeBackend is a safe scaffold in v0.7. It does not submit hardware jobs yet.")
print("This is intentional so the package works safely without credentials.")
