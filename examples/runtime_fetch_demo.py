from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_runtime_fetch_demo, runtime_package_available

print("AZM-QOS v4.6 Runtime Fetch Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "runtime_fetch_demo"
result = run_runtime_fetch_demo(out_dir, backend_name="ibm_fez", rounds=2, shots=64)

print("qiskit-ibm-runtime available:", runtime_package_available())
print(result.summary())
print()
for item in result.fetch_records:
    print(item.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
