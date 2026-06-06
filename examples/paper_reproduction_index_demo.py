from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import export_paper_reproduction_index

print("AZM-QOS v5.0 Paper Reproduction Index Demo")
print("=" * 70)
path = export_paper_reproduction_index(ROOT / "outputs" / "paper_reproduction_index_demo" / "paper_reproduction_index.md")
print("paper_reproduction_index:", path)
