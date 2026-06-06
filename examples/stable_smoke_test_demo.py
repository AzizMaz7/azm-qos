from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_stable_smoke_test

print("AZM-QOS v4.0 Stable Smoke Test Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "stable_smoke_test_demo"
result = run_stable_smoke_test(out_dir)

print(result.summary())
print()
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
