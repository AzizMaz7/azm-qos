from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import shutil

from .real_terms import run_real_term_research_pipeline, load_registry_for_research
from .shot_scaling import run_endvqs_shot_scaling_package
from .captions import (
    caption_for_m_matrix,
    caption_for_v_vector,
    caption_for_shot_scaling,
    caption_for_matching_failure,
    save_captions,
)

@dataclass
class PublicationFigurePackage:
    output_dir: str
    figures_dir: str
    tables_dir: str
    captions_dir: str
    reports_dir: str
    artifacts: dict[str, str]
    metadata: dict[str, Any]

    def summary(self):
        return (
            "PublicationFigurePackage\n"
            f"  output_dir: {self.output_dir}\n"
            f"  figures: {self.figures_dir}\n"
            f"  tables: {self.tables_dir}\n"
            f"  captions: {self.captions_dir}\n"
            f"  reports: {self.reports_dir}\n"
            f"  artifacts: {len(self.artifacts)}"
        )

def _copy_if_exists(src, dst):
    src = Path(src)
    dst = Path(dst)
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return str(dst)
    return str(src)

def make_publication_summary_report(package: PublicationFigurePackage, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v2.2 Publication Figure Package",
        "",
        "## Package summary",
        "",
        "```text",
        package.summary(),
        "```",
        "",
        "## Artifacts",
        "",
    ]
    for key, value in package.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    lines.extend([
        "",
        "## Suggested manuscript usage",
        "",
        "Use the files in `figures/` for manuscript figures, `tables/` for numerical values, and `captions/` for Markdown/LaTeX captions.",
        "",
        "## Scientific note",
        "",
        "If the END/VQS registry still contains placeholder terms, these figures are software-validation figures, not final physics figures.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

def build_publication_figure_package(
    output_dir,
    component_registry_json=None,
    term_registry_json=None,
    shots: int = 128,
    repeats: int = 2,
    n_rounds: int = 3,
    n_trials: int = 5,
    measurement_error_probability: float = 0.05,
    shot_powers=(6, 8, 10),
    seed: int | None = 123,
):
    """Build a thesis/manuscript-ready figure package."""
    output_dir = Path(output_dir)
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    captions_dir = output_dir / "captions"
    reports_dir = output_dir / "reports"
    raw_dir = output_dir / "raw_run"

    for d in [figures_dir, tables_dir, captions_dir, reports_dir, raw_dir]:
        d.mkdir(parents=True, exist_ok=True)

    run = run_real_term_research_pipeline(
        output_dir=raw_dir,
        term_registry_json=term_registry_json,
        component_registry_json=component_registry_json,
        shots=shots,
        repeats=repeats,
        n_rounds=n_rounds,
        n_trials=n_trials,
        measurement_error_probability=measurement_error_probability,
        seed=seed,
    )

    registry_load = load_registry_for_research(
        term_registry_json=term_registry_json,
        component_registry_json=component_registry_json,
    )

    shot_result, shot_artifacts = run_endvqs_shot_scaling_package(
        registry_load.registry,
        output_dir=raw_dir / "shot_scaling",
        shot_powers=shot_powers,
        repeats=max(2, repeats),
        seed=seed,
    )

    artifacts = {}
    artifacts["figure_m_matrix"] = _copy_if_exists(run.artifacts["m_matrix_figure"], figures_dir / "fig1_m_matrix.png")
    artifacts["figure_v_vector"] = _copy_if_exists(run.artifacts["v_vector_figure"], figures_dir / "fig2_v_vector.png")
    artifacts["figure_shot_scaling"] = _copy_if_exists(shot_artifacts["shot_scaling_figure"], figures_dir / "fig3_shot_scaling_loglog.png")
    artifacts["figure_matching_failure"] = _copy_if_exists(run.artifacts["matching_failure_figure"], figures_dir / "fig4_matching_failure_rates.png")

    artifacts["table_m_matrix"] = _copy_if_exists(run.artifacts["m_matrix_csv"], tables_dir / "table_m_matrix.csv")
    artifacts["table_v_vector"] = _copy_if_exists(run.artifacts["v_vector_csv"], tables_dir / "table_v_vector.csv")
    artifacts["table_matching_benchmark"] = _copy_if_exists(run.artifacts["matching_benchmark_csv"], tables_dir / "table_matching_benchmark.csv")
    artifacts["table_shot_scaling"] = _copy_if_exists(shot_artifacts["shot_scaling_csv"], tables_dir / "table_shot_scaling.csv")

    captions = [
        caption_for_m_matrix("figures/fig1_m_matrix.png"),
        caption_for_v_vector("figures/fig2_v_vector.png"),
        caption_for_shot_scaling("figures/fig3_shot_scaling_loglog.png"),
        caption_for_matching_failure("figures/fig4_matching_failure_rates.png"),
    ]
    artifacts.update({f"captions_{k}": v for k, v in save_captions(captions, captions_dir).items()})

    package = PublicationFigurePackage(
        output_dir=str(output_dir),
        figures_dir=str(figures_dir),
        tables_dir=str(tables_dir),
        captions_dir=str(captions_dir),
        reports_dir=str(reports_dir),
        artifacts=artifacts,
        metadata={
            "raw_run_dir": str(raw_dir),
            "shot_scaling_points": len(shot_result.points),
            "registry_source": registry_load.source_type,
        },
    )

    artifacts["publication_summary_report"] = str(make_publication_summary_report(package, reports_dir / "publication_summary.md"))

    manifest = {
        "package": "AZM-QOS v2.2 publication figure package",
        "metadata": package.metadata,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "publication_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    artifacts["publication_manifest"] = str(manifest_path)

    return PublicationFigurePackage(
        output_dir=str(output_dir),
        figures_dir=str(figures_dir),
        tables_dir=str(tables_dir),
        captions_dir=str(captions_dir),
        reports_dir=str(reports_dir),
        artifacts=artifacts,
        metadata=package.metadata,
    )
