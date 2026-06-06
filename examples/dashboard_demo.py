from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import build_dashboard_package

print("AZM-QOS v2.8 Dashboard Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "dashboard_demo"
package = build_dashboard_package(out_dir)

print(package.summary_text())
print()
print("Artifacts:")
for key, value in package.artifacts.items():
    print(f"  {key}: {value}")
