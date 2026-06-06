from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import load_registry_for_research, run_endvqs_shot_scaling_package

print("AZM-QOS v2.2 Shot-Scaling Demo")
print("=" * 70)

template = ROOT / "templates" / "endvqs_real_terms_template.json"
load_result = load_registry_for_research(component_registry_json=template)

out_dir = ROOT / "outputs" / "shot_scaling_demo"
result, artifacts = run_endvqs_shot_scaling_package(
    load_result.registry,
    output_dir=out_dir,
    shot_powers=(6, 8, 10),
    repeats=3,
    seed=123,
)

print(result.summary())
print()
print("Artifacts:")
for key, value in artifacts.items():
    print(f"  {key}: {value}")
