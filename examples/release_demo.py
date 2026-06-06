from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_release_demo

print("AZM-QOS v4.9 Release Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "release_demo"
result = run_release_demo(out_dir)

print(result.summary())
print()
print(result.validation.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
