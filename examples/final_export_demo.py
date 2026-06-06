from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_final_export_demo

print("AZM-QOS v4.8 Final Export Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "final_export_demo"
result = run_final_export_demo(out_dir)

print(result.summary())
print()
for fig in result.figures:
    print(fig.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
