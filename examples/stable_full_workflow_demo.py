from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pathlib import Path
from azmqos_research import (
    ensure_production_config,
    load_production_spec,
    save_production_spec,
    run_stable_workflow,
)

print("AZM-QOS v4.0 Stable Full Workflow Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "stable_full_workflow_demo"
config_path, created = ensure_production_config(out_dir / "production_project", project_name="demo_stable_full")

spec = load_production_spec(config_path)
spec.component_registry_path = str(ROOT / "templates" / "endvqs_real_terms_template.json")
save_production_spec(spec, config_path)

result = run_stable_workflow(config_path, backend="fallback", max_components=2, shots=64)

print(result.summary())
print()
print("Artifacts:")
for key, value in result.artifacts.items():
    print(f"  {key}: {value}")
