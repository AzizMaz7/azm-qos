from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import make_pauli_compile_demo

print("AZM-QOS v3.4 Pauli-Term Compiler Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "pauli_term_compiler_demo"
result = make_pauli_compile_demo(out_dir)

print(result.summary())
print()
for group in result.groups:
    print(group.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
