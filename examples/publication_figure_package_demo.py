from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import build_publication_figure_package

print("AZM-QOS v2.2 Publication Figure Package Demo")
print("=" * 70)

template = ROOT / "templates" / "endvqs_real_terms_template.json"
out_dir = ROOT / "outputs" / "publication_figure_package_demo"

package = build_publication_figure_package(
    output_dir=out_dir,
    component_registry_json=template,
    shots=128,
    repeats=2,
    n_rounds=3,
    n_trials=5,
    shot_powers=(6, 8, 10),
    seed=123,
)

print(package.summary())
print()
print("Artifacts:")
for key, value in package.artifacts.items():
    print(f"  {key}: {value}")
