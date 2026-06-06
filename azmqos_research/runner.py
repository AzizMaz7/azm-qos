from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from azmqos_pipeline import run_endvqs_detector_error_model_pipeline
from .manifests import create_experiment_manifest, save_manifest_json
from .tables import export_m_matrix_csv, export_v_vector_csv, export_benchmark_table_csv
from .figures import plot_m_matrix, plot_v_vector, plot_matching_failure_rates
from .reports import make_markdown_research_report, make_latex_research_report
from .bundles import create_reproducibility_bundle

@dataclass
class ResearchRunResult:
    manifest: Any
    M: Any
    V: Any
    detector_error_model: Any
    matching_benchmark_result: Any
    artifacts: dict[str, str]

    def summary(self):
        return (
            "ResearchRunResult\n"
            f"  manifest: {self.manifest.experiment_id}\n"
            f"  M shape: {self.M.shape}\n"
            f"  V shape: {self.V.shape}\n"
            f"  artifacts: {len(self.artifacts)}"
        )

def run_research_platform_pipeline(
    output_dir,
    shots: int = 64,
    repeats: int = 1,
    n_rounds: int = 3,
    n_trials: int = 5,
    measurement_error_probability: float = 0.05,
    seed: int | None = 123,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = run_endvqs_detector_error_model_pipeline(
        shots=shots,
        repeats=repeats,
        n_rounds=n_rounds,
        n_trials=n_trials,
        measurement_error_probability=measurement_error_probability,
        seed=seed,
    )

    manifest = create_experiment_manifest(
        name="azmqos_v2_0_research_platform_run",
        configuration={
            "shots": shots,
            "repeats": repeats,
            "n_rounds": n_rounds,
            "n_trials": n_trials,
            "measurement_error_probability": measurement_error_probability,
            "seed": seed,
        },
    )

    M = pipeline.detector_graph_pipeline_result.circuit_pipeline_result.M
    V = pipeline.detector_graph_pipeline_result.circuit_pipeline_result.V
    detector_model = pipeline.detector_error_model
    benchmark = pipeline.matching_benchmark_result

    artifacts = {}
    artifacts["m_matrix_csv"] = str(export_m_matrix_csv(M, output_dir / "m_matrix.csv"))
    artifacts["v_vector_csv"] = str(export_v_vector_csv(V, output_dir / "v_vector.csv"))
    artifacts["matching_benchmark_csv"] = str(export_benchmark_table_csv(benchmark, output_dir / "matching_benchmark.csv"))
    artifacts["m_matrix_figure"] = str(plot_m_matrix(M, output_dir / "m_matrix.png"))
    artifacts["v_vector_figure"] = str(plot_v_vector(V, output_dir / "v_vector.png"))
    artifacts["matching_failure_figure"] = str(plot_matching_failure_rates(benchmark, output_dir / "matching_failure_rates.png"))

    # Create a temporary result object before report generation.
    result = ResearchRunResult(
        manifest=manifest,
        M=M,
        V=V,
        detector_error_model=detector_model,
        matching_benchmark_result=benchmark,
        artifacts=artifacts,
    )

    artifacts["markdown_report"] = str(make_markdown_research_report(result, output_dir / "research_report.md"))
    artifacts["latex_report"] = str(make_latex_research_report(result, output_dir / "research_report.tex"))

    manifest.artifacts = artifacts
    artifacts["manifest_json"] = str(save_manifest_json(manifest, output_dir / "experiment_manifest.json"))

    # Save detector-error-model text too.
    dem_path = output_dir / "detector_error_model.dem.txt"
    dem_path.write_text(detector_model.to_text(), encoding="utf-8")
    artifacts["detector_error_model_text"] = str(dem_path)
    save_manifest_json(manifest, output_dir / "experiment_manifest.json")

    bundle = create_reproducibility_bundle(output_dir, output_dir / "reproducibility_bundle.zip", manifest)
    artifacts["reproducibility_bundle"] = bundle.bundle_path
    save_manifest_json(manifest, output_dir / "experiment_manifest.json")

    return ResearchRunResult(
        manifest=manifest,
        M=M,
        V=V,
        detector_error_model=detector_model,
        matching_benchmark_result=benchmark,
        artifacts=artifacts,
    )
