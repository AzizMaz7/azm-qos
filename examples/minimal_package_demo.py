from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_minimal_package_demo

print("AZM-QOS v4.9 Minimal Package Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "minimal_package_demo"
archive, manifest = run_minimal_package_demo(out_dir)

print("Archive:", archive)
print("Manifest:", manifest)
