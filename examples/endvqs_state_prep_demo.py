from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import make_stateprep_demo

print("AZM-QOS v3.7 END/VQS State-Preparation Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "endvqs_state_prep_demo"
plan, artifacts = make_stateprep_demo(out_dir)

print(plan.summary())
print()
for op in plan.operations:
    print(op.summary())
print()
print("Artifacts:")
for key, value in artifacts.items():
    print(f"  {key}: {value}")
