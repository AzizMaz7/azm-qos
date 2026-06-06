from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_real_term_research_pipeline

print("AZM-QOS v2.1 Real-Term Research Demo")
print("=" * 70)

template = ROOT / "templates" / "endvqs_real_terms_template.json"
out_dir = ROOT / "outputs" / "real_term_research_demo"

result = run_real_term_research_pipeline(
    output_dir=out_dir,
    component_registry_json=template,
    shots=128,
    repeats=2,
    n_rounds=3,
    n_trials=5,
    measurement_error_probability=0.05,
    seed=123,
)

print(result.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
