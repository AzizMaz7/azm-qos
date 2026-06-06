from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

@dataclass
class FigureCaption:
    figure_id: str
    title: str
    caption: str
    filename: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def markdown(self):
        return f"**{self.figure_id}. {self.title}.** {self.caption}"

    def latex(self):
        safe_caption = self.caption.replace("_", "\\_")
        safe_title = self.title.replace("_", "\\_")
        safe_file = self.filename.replace("\\", "/")
        return (
            "\\begin{figure}[htbp]\n"
            "\\centering\n"
            f"\\includegraphics[width=0.85\\linewidth]{{{safe_file}}}\n"
            f"\\caption{{\\textbf{{{safe_title}.}} {safe_caption}}}\n"
            f"\\label{{fig:{self.figure_id.lower().replace(' ', '_')}}}\n"
            "\\end{figure}\n"
        )

def caption_for_m_matrix(filename="m_matrix.png"):
    return FigureCaption(
        figure_id="Figure 1",
        title="Assembled END/VQS M matrix",
        filename=filename,
        caption=(
            "Heat-map representation of the assembled END/VQS symplectic matrix M. "
            "Each entry is estimated from the Pauli-decomposed workload registry and assembled into matrix form."
        ),
        metadata={"quantity": "M"},
    )

def caption_for_v_vector(filename="v_vector.png"):
    return FigureCaption(
        figure_id="Figure 2",
        title="Assembled END/VQS V vector",
        filename=filename,
        caption=(
            "Bar-plot representation of the assembled END/VQS vector V. "
            "The entries summarize force/gradient-style Pauli workloads evaluated by the AZM-QOS runtime."
        ),
        metadata={"quantity": "V"},
    )

def caption_for_shot_scaling(filename="shot_scaling_loglog.png"):
    return FigureCaption(
        figure_id="Figure 3",
        title="Shot-scaling error analysis",
        filename=filename,
        caption=(
            "Log-log shot-scaling analysis for repeated END/VQS observable estimation. "
            "The plotted absolute error trend is expected to decrease with the characteristic finite-shot sampling scale."
        ),
        metadata={"quantity": "shot_scaling"},
    )

def caption_for_matching_failure(filename="matching_failure_rates.png"):
    return FigureCaption(
        figure_id="Figure 4",
        title="Matching-decoder failure-rate benchmark",
        filename=filename,
        caption=(
            "Detector-error probability sweep for the matching-decoder scaffold. "
            "The logical failure rate is estimated from repeated sampled detector-event trials."
        ),
        metadata={"quantity": "qec_benchmark"},
    )

def save_captions(captions, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "figure_captions.md"
    tex_path = output_dir / "figure_captions.tex"
    json_path = output_dir / "figure_captions.json"

    md_path.write_text("\n\n".join(c.markdown() for c in captions) + "\n", encoding="utf-8")
    tex_path.write_text("\n".join(c.latex() for c in captions) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps([c.__dict__ for c in captions], indent=2), encoding="utf-8")

    return {"markdown": str(md_path), "latex": str(tex_path), "json": str(json_path)}
