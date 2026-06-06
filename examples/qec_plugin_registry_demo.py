from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos import default_plugin_registry

registry = default_plugin_registry()

print("AZM-QOS v0.9 Plugin Registry with QEC")
print("=" * 70)
for name, info in registry.list_plugins().items():
    print(f"{name:24s} | {info.domain:8s} | {info.version}")
