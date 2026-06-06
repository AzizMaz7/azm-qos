from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_research_platform_pipeline

print("AZM-QOS v2.0 Research Platform Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "research_platform_demo"
result = run_research_platform_pipeline(
    output_dir=out_dir,
    shots=64,
    repeats=1,
    n_rounds=3,
    n_trials=5,
    measurement_error_probability=0.05,
    seed=123,
)

print(result.summary())
print()
print("Artifacts:")
for key, path in result.artifacts.items():
    print(f"  {key}: {path}")
