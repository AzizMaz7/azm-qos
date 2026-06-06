from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_qec_hardware_demo

print("AZM-QOS v4.4 QEC Hardware Transpile Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "qec_hardware_transpile_demo"
result = run_qec_hardware_demo(out_dir, backend_name="ibm_fez", code_name="repetition3", rounds=3, shots=64)

print(result.summary())
print()
for item in result.resources:
    print(item.summary())
print()
for item in result.job_manifests:
    print(item.summary())
