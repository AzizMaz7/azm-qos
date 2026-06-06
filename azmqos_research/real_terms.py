from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import csv
import json

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_endvqs import (
    default_endvqs_registry,
    load_term_registry_json,
    load_component_registry_json,
    component_registry_to_term_registry,
    validate_term_registry,
    m_symmetry_diagnostics,
    build_all_endvqs_workloads,
    assemble_m_matrix,
    assemble_v_vector,
)
from azmqos_qec import (
    build_repetition_detector_graph,
    detector_graph_to_error_model,
    run_matching_decoder_benchmark,
)
from .manifests import create_experiment_manifest, save_manifest_json
from .tables import export_m_matrix_csv, export_v_vector_csv, export_benchmark_table_csv
from .figures import plot_m_matrix, plot_v_vector, plot_matching_failure_rates
from .bundles import create_reproducibility_bundle

@dataclass
class RealTermRegistryLoadResult:
    registry: Any
    source_type: str
    source_path: str | None
    validation: Any
    symmetry_diagnostics: dict

    def summary(self):
        return (
            f"RealTermRegistryLoadResult(source_type={self.source_type}, "
            f"source_path={self.source_path}, validation_ok={self.validation.ok})"
        )

@dataclass
class RealTermResearchRunResult:
    manifest: Any
    registry_load_result: RealTermRegistryLoadResult
    M: Any
    V: Any
    endvqs_results: list
    detector_error_model: Any
    matching_benchmark_result: Any
    artifacts: dict[str, str]

    def summary(self):
        return (
            "RealTermResearchRunResult\n"
            f"  registry: {self.registry_load_result.source_type}\n"
            f"  validation ok: {self.registry_load_result.validation.ok}\n"
            f"  M shape: {self.M.shape}\n"
            f"  V shape: {self.V.shape}\n"
            f"  END/VQS jobs: {len(self.endvqs_results)}\n"
            f"  artifacts: {len(self.artifacts)}"
        )

def load_registry_for_research(term_registry_json=None, component_registry_json=None, allow_default: bool = True):
    """Load an END/VQS registry from term JSON, component JSON, or default proxy terms."""
    source_path = None
    if term_registry_json is not None:
        source_path = str(term_registry_json)
        registry = load_term_registry_json(term_registry_json)
        source_type = "term_registry_json"
    elif component_registry_json is not None:
        source_path = str(component_registry_json)
        component_registry = load_component_registry_json(component_registry_json)
        registry = component_registry_to_term_registry(component_registry)
        source_type = "component_registry_json"
    elif allow_default:
        registry = default_endvqs_registry()
        source_type = "default_proxy_registry"
    else:
        raise ValueError("Provide term_registry_json or component_registry_json, or set allow_default=True.")

    validation = validate_term_registry(registry)
    symmetry = m_symmetry_diagnostics(registry)

    return RealTermRegistryLoadResult(
        registry=registry,
        source_type=source_type,
        source_path=source_path,
        validation=validation,
        symmetry_diagnostics=symmetry,
    )

def export_term_audit_csv(registry, path):
    """Export all M/V Pauli terms for human audit."""
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["quantity", "i", "j", "label", "pauli", "coeff_real", "coeff_imag", "n_qubits"])
        for (i, j), terms in registry.m_terms.items():
            for term in terms:
                writer.writerow(["M", i, j, term.name, term.pauli, term.coeff.real, term.coeff.imag, term.n_qubits])
        for i, terms in registry.v_terms.items():
            for term in terms:
                writer.writerow(["V", i, "", term.name, term.pauli, term.coeff.real, term.coeff.imag, term.n_qubits])
    return path

def make_real_term_validation_report(load_result: RealTermRegistryLoadResult, output_path):
    output_path = Path(output_path)
    serializable_symmetry = {str(k): v for k, v in load_result.symmetry_diagnostics.items()}
    lines = [
        "# AZM-QOS v2.1 Real END/VQS Term Validation Report",
        "",
        "## Registry source",
        "",
        f"- Source type: `{load_result.source_type}`",
        f"- Source path: `{load_result.source_path}`",
        "",
        "## Validation",
        "",
        "```text",
        load_result.validation.summary(),
        "```",
        "",
        "## M-matrix symmetry diagnostics",
        "",
        "```json",
        json.dumps(serializable_symmetry, indent=2),
        "```",
        "",
        "## Scientific note",
        "",
        "This report validates structure, dimensions, Pauli strings, and coefficient sanity. It does not prove the physics is correct; that must come from your analytic derivation.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

def make_real_term_markdown_report(result: RealTermResearchRunResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v2.1 Real-Term Research Report",
        "",
        "## Run summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Registry validation",
        "",
        "```text",
        result.registry_load_result.validation.summary(),
        "```",
        "",
        "## M matrix",
        "",
        "```text",
        str(result.M),
        "```",
        "",
        "## V vector",
        "",
        "```text",
        str(result.V),
        "```",
        "",
        "## Detector error model",
        "",
        "```text",
        result.detector_error_model.summary(),
        "```",
        "",
        "## Matching benchmark",
        "",
        "```text",
        result.matching_benchmark_result.summary(),
        "```",
        "",
        "## Artifacts",
        "",
    ]
    for key, value in result.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    lines.extend([
        "",
        "## Important note",
        "",
        "If you used `templates/endvqs_real_terms_template.json` without replacing the placeholder coefficients, this is still a software-validation run, not final physics.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

def make_real_term_latex_report(result: RealTermResearchRunResult, output_path):
    output_path = Path(output_path)
    tex = f"""
\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{amsmath}}
\\usepackage{{booktabs}}
\\title{{AZM-QOS v2.1 Real END/VQS Term Research Report}}
\\author{{AZM-QOS Automated Research Workflow}}
\\date{{\\today}}
\\begin{{document}}
\\maketitle

\\begin{{abstract}}
This report summarizes a real-term END/VQS registry workflow in AZM-QOS v2.1. The workflow loads a user-provided Pauli-term registry, validates it, executes END/VQS workloads, assembles the matrix M and vector V, and attaches detector-error-model and matching-decoder benchmark diagnostics.
\\end{{abstract}}

\\section{{Registry Validation}}
\\begin{{verbatim}}
{result.registry_load_result.validation.summary()}
\\end{{verbatim}}

\\section{{Assembled END/VQS Objects}}
\\subsection{{M Matrix}}
\\begin{{verbatim}}
{result.M}
\\end{{verbatim}}

\\subsection{{V Vector}}
\\begin{{verbatim}}
{result.V}
\\end{{verbatim}}

\\section{{QEC Diagnostics}}
\\begin{{verbatim}}
{result.detector_error_model.summary()}

{result.matching_benchmark_result.summary()}
\\end{{verbatim}}

\\section{{Limitations}}
Structural validation does not prove that the input Pauli decomposition is analytically correct. The Pauli coefficients must be checked against the user's END/VQS derivation.

\\end{{document}}
"""
    output_path.write_text(tex.strip() + "\n", encoding="utf-8")
    return output_path

def run_real_term_research_pipeline(
    output_dir,
    term_registry_json=None,
    component_registry_json=None,
    shots: int = 256,
    repeats: int = 5,
    n_rounds: int = 5,
    n_trials: int = 20,
    measurement_error_probability: float = 0.05,
    seed: int | None = 123,
    allow_default: bool = True,
):
    """Run the reproducible research workflow using a custom END/VQS registry."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    load_result = load_registry_for_research(
        term_registry_json=term_registry_json,
        component_registry_json=component_registry_json,
        allow_default=allow_default,
    )

    if not load_result.validation.ok:
        make_real_term_validation_report(load_result, output_dir / "real_term_validation_report.md")
        raise ValueError("Registry validation failed. See real_term_validation_report.md.")

    manager = RuntimeManager()
    workloads = build_all_endvqs_workloads(registry=load_result.registry)
    endvqs_results = [
        manager.run(w, "shot_simulator", RuntimeConfig(shots=shots, repeats=repeats, seed=seed))
        for w in workloads
    ]

    M = assemble_m_matrix(endvqs_results, dimension=load_result.registry.dimension)
    V = assemble_v_vector(endvqs_results, dimension=load_result.registry.dimension)

    graph = build_repetition_detector_graph(
        ["S_ZZI", "S_IZZ"],
        n_rounds=n_rounds,
        measurement_error_probability=measurement_error_probability,
    )
    detector_model = detector_graph_to_error_model(
        graph,
        default_probability=measurement_error_probability,
        logical_labels={"0": "logical_failure_placeholder"},
    )
    benchmark = run_matching_decoder_benchmark(
        probabilities=[0.0, measurement_error_probability, min(0.25, 2 * measurement_error_probability)],
        n_trials=n_trials,
        n_rounds=n_rounds,
        seed=seed,
    )

    manifest = create_experiment_manifest(
        name="azmqos_v2_1_real_term_research_run",
        configuration={
            "registry_source_type": load_result.source_type,
            "registry_source_path": load_result.source_path,
            "shots": shots,
            "repeats": repeats,
            "n_rounds": n_rounds,
            "n_trials": n_trials,
            "measurement_error_probability": measurement_error_probability,
            "seed": seed,
        },
    )

    artifacts = {}
    artifacts["term_audit_csv"] = str(export_term_audit_csv(load_result.registry, output_dir / "term_audit.csv"))
    artifacts["validation_report"] = str(make_real_term_validation_report(load_result, output_dir / "real_term_validation_report.md"))
    artifacts["m_matrix_csv"] = str(export_m_matrix_csv(M, output_dir / "m_matrix.csv"))
    artifacts["v_vector_csv"] = str(export_v_vector_csv(V, output_dir / "v_vector.csv"))
    artifacts["matching_benchmark_csv"] = str(export_benchmark_table_csv(benchmark, output_dir / "matching_benchmark.csv"))
    artifacts["m_matrix_figure"] = str(plot_m_matrix(M, output_dir / "m_matrix.png"))
    artifacts["v_vector_figure"] = str(plot_v_vector(V, output_dir / "v_vector.png"))
    artifacts["matching_failure_figure"] = str(plot_matching_failure_rates(benchmark, output_dir / "matching_failure_rates.png"))

    result = RealTermResearchRunResult(
        manifest=manifest,
        registry_load_result=load_result,
        M=M,
        V=V,
        endvqs_results=endvqs_results,
        detector_error_model=detector_model,
        matching_benchmark_result=benchmark,
        artifacts=artifacts,
    )

    artifacts["markdown_report"] = str(make_real_term_markdown_report(result, output_dir / "real_term_research_report.md"))
    artifacts["latex_report"] = str(make_real_term_latex_report(result, output_dir / "real_term_research_report.tex"))

    detector_path = output_dir / "detector_error_model.dem.txt"
    detector_path.write_text(detector_model.to_text(), encoding="utf-8")
    artifacts["detector_error_model_text"] = str(detector_path)

    manifest.artifacts = artifacts
    artifacts["manifest_json"] = str(save_manifest_json(manifest, output_dir / "experiment_manifest.json"))

    bundle = create_reproducibility_bundle(output_dir, output_dir / "real_term_reproducibility_bundle.zip", manifest)
    artifacts["reproducibility_bundle"] = bundle.bundle_path
    save_manifest_json(manifest, output_dir / "experiment_manifest.json")

    return RealTermResearchRunResult(
        manifest=manifest,
        registry_load_result=load_result,
        M=M,
        V=V,
        endvqs_results=endvqs_results,
        detector_error_model=detector_model,
        matching_benchmark_result=benchmark,
        artifacts=artifacts,
    )
