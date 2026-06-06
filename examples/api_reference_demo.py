from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import export_api_reference_markdown

print("AZM-QOS v5.0 API Reference Demo")
print("=" * 70)
path = export_api_reference_markdown(ROOT / "outputs" / "api_reference_demo" / "api_reference.md")
print("api_reference:", path)
