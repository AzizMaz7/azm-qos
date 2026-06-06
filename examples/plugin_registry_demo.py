from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import default_plugin_registry, save_plugin_registry, make_plugin_registry_report

print("AZM-QOS v3.0 Plugin Registry Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "plugin_registry_demo"
out_dir.mkdir(parents=True, exist_ok=True)

registry = default_plugin_registry()
json_path = save_plugin_registry(registry, out_dir / "plugin_registry.json")
report_path = make_plugin_registry_report(registry, out_dir / "plugin_registry_report.md")

print(registry.summary())
print()
for plugin in registry.plugins:
    print(plugin.summary())

print()
print("Saved:", json_path)
print("Report:", report_path)
