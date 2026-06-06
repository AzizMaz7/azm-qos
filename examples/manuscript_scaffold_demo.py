from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from azmqos_research import (
    FinalFigureRecord,
    make_latex_manuscript_scaffold,
    make_thesis_appendix_scaffold,
)

print("AZM-QOS v4.8 Manuscript Scaffold Demo")
print("=" * 70)

out_dir = ROOT / "outputs" / "manuscript_scaffold_demo"
figures = [
    FinalFigureRecord(
        "fig_demo",
        "Demo figure",
        "figures/demo.png",
        caption="Demo caption for the manuscript scaffold.",
    )
]
manuscript = make_latex_manuscript_scaffold("demo_project", figures, out_dir / "manuscript.tex")
appendix = make_thesis_appendix_scaffold("demo_project", {"manuscript": str(manuscript)}, out_dir / "thesis_appendix.md")

print("Manuscript:", manuscript)
print("Appendix:", appendix)
