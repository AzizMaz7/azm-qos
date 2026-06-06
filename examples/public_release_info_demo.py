from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import run_public_release_info

print("AZM-QOS v5.0 Public Release Info Demo")
print("=" * 70)
artifacts = run_public_release_info(ROOT / "outputs" / "public_release_info_demo")
for key, value in artifacts.items():
    print(f"{key}: {value}")
