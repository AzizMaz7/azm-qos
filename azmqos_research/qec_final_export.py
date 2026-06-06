from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import os
import platform
import shutil
import sys
import textwrap
import time
import zipfile

from .production import load_production_spec
from .qec_hardware_analysis import (
    HardwareAnalysisResult,
    run_hardware_analysis_demo,
    run_production_hardware_analysis,
)


@dataclass
class FinalFigureRecord:
    figure_id: str
    title: str
    path: str
    source_artifact: str | None = None
    caption: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "FinalFigureRecord\n"
            f"  figure_id: {self.figure_id}\n"
            f"  title: {self.title}\n"
            f"  path: {self.path}\n"
            f"  source: {self.source_artifact}"
        )


@dataclass
class ReproducibilityChecklist:
    project_name: str
    items: dict[str, bool]
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        passed = sum(1 for v in self.items.values() if v)
        return (
            "ReproducibilityChecklist\n"
            f"  project: {self.project_name}\n"
            f"  passed: {passed}/{len(self.items)}\n"
            f"  notes: {self.notes}"
        )


@dataclass
class VersionLockfile:
    package_version: str
    python_version: str
    platform: str
    created_at_unix: float
    important_files: dict[str, str] = field(default_factory=dict)
    installed_packages_hint: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            "VersionLockfile\n"
            f"  package_version: {self.package_version}\n"
            f"  python_version: {self.python_version}\n"
            f"  platform: {self.platform}\n"
            f"  important_files: {len(self.important_files)}"
        )


@dataclass
class FinalExportResult:
    project_name: str
    output_dir: str
    figures: list[FinalFigureRecord]
    checklist: ReproducibilityChecklist
    lockfile: VersionLockfile
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "FinalExportResult\n"
            f"  project: {self.project_name}\n"
            f"  output_dir: {self.output_dir}\n"
            f"  figures: {len(self.figures)}\n"
            f"  checklist_items: {len(self.checklist.items)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def read_package_version(package_root: Path) -> str:
    pyproject = package_root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    text = pyproject.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("version"):
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def collect_project_artifacts(project_dir) -> dict[str, str]:
    project_dir = Path(project_dir)
    patterns = {
        "hardware_analysis_report": "hardware_analysis/hardware_analysis_report.md",
        "hardware_analysis_manifest": "hardware_analysis/production_hardware_analysis_manifest.json",
        "hardware_run_summary": "hardware_analysis/hardware_run_summary.json",
        "calibration_metadata": "hardware_analysis/calibration_metadata.json",
        "counts_confidence_intervals": "hardware_analysis/counts_confidence_intervals.csv",
        "logical_failure_bands": "hardware_analysis/logical_failure_bands.csv",
        "logical_failure_bands_figure": "hardware_analysis/logical_failure_bands.png",
        "real_vs_synthetic_figure": "hardware_analysis/real_vs_synthetic_summary.png",
        "runtime_sync_report": "runtime_sync/runtime_sync_report.md",
        "sync_comparisons": "runtime_sync/sync_comparisons.csv",
        "qec_hardware_report": "qec_hardware_dry_run/qec_hardware_report.md",
        "ft_qec_report": "ft_qec/ft_qec_report.md",
        "qec_decoder_report": "qec_decoder/qec_decoder_report.md",
    }
    found = {}
    for key, rel in patterns.items():
        path = project_dir / rel
        if path.exists():
            found[key] = str(path)
    return found


def copy_final_figures(analysis: HardwareAnalysisResult, output_dir) -> list[FinalFigureRecord]:
    output_dir = Path(output_dir)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    figure_specs = [
        ("fig_failure_bands", "Logical failure-rate confidence bands", analysis.artifacts.get("failure_bands_figure"), "Wilson-style confidence bands for the logical failure proxy."),
        ("fig_source_separation", "Real-vs-synthetic hardware-record separation", analysis.artifacts.get("source_separation_figure"), "Separation between real Runtime records, synthetic fallback records, and cached records."),
    ]

    records: list[FinalFigureRecord] = []
    for fig_id, title, source, caption in figure_specs:
        if source and Path(source).exists():
            target = figures_dir / f"{fig_id}{Path(source).suffix}"
            shutil.copy2(source, target)
            records.append(FinalFigureRecord(fig_id, title, str(target), source_artifact=source, caption=caption))
    return records


def make_summary_figure_from_artifacts(analysis: HardwareAnalysisResult, output_dir) -> FinalFigureRecord | None:
    output_dir = Path(output_dir)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / "fig_hardware_summary.png"
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = figures_dir / "fig_hardware_summary.txt"
        txt.write_text(analysis.run_summary.summary(), encoding="utf-8")
        return FinalFigureRecord(
            "fig_hardware_summary",
            "Hardware analysis summary",
            str(txt),
            caption="Text summary fallback because matplotlib is unavailable.",
        )

    labels = ["passed", "failed", "synthetic", "runtime"]
    values = [
        analysis.run_summary.passed_consistency,
        analysis.run_summary.failed_consistency,
        analysis.run_summary.synthetic_records,
        analysis.run_summary.runtime_records,
    ]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(labels, values)
    ax.set_ylabel("records")
    ax.set_title("Final QEC hardware-analysis summary")
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return FinalFigureRecord(
        "fig_hardware_summary",
        "Final QEC hardware-analysis summary",
        str(path),
        caption="Summary of consistency checks and real-vs-synthetic record types.",
    )


def make_latex_manuscript_scaffold(project_name: str, figures: list[FinalFigureRecord], output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figure_blocks = []
    for fig in figures:
        rel = Path(fig.path).name
        figure_blocks.append(rf"""
\begin{{figure}}[ht]
    \centering
    \includegraphics[width=0.85\linewidth]{{figures/{rel}}}
    \caption{{{fig.caption or fig.title}}}
    \label{{fig:{fig.figure_id}}}
\end{{figure}}
""")

    text = rf"""
\documentclass[11pt]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{amsmath,amssymb}}
\usepackage{{hyperref}}

\title{{AZM-QOS END/VQS and QEC Hardware-Analysis Workflow}}
\author{{AZM-QOS Research Export}}
\date{{\today}}

\begin{{document}}
\maketitle

\begin{{abstract}}
This scaffold summarizes the AZM-QOS END/VQS workflow with QEC-aware logical estimators,
hardware-style synchronization, confidence-interval analysis, and final reproducibility exports.
Synthetic fallback results are clearly separated from real Runtime records.
\end{{abstract}}

\section{{Introduction}}
This manuscript scaffold was generated for project \texttt{{{project_name}}}.
It is intended as a starting point for a paper or internal report.

\section{{Methods}}
The workflow includes Pauli compilation, END/VQS state-preparation scaffolds, derivative estimators,
QEC logical mapping, syndrome decoding, fault-tolerant QEC scaffolds, hardware dry-run manifests,
Runtime-style synchronization, and final hardware-analysis exports.

\section{{Results}}
{''.join(figure_blocks)}

\section{{Reproducibility}}
The final export includes a command summary, version lockfile, reproducibility checklist, and archive.

\section{{Limitations}}
Synthetic-only analyses validate the workflow but should not be interpreted as hardware evidence.
Device-specific calibration data and real Runtime results should be imported for publication-quality conclusions.

\bibliographystyle{{unsrt}}
\begin{{thebibliography}}{{9}}
\bibitem{{qiskit}} Qiskit contributors, Qiskit: An open-source framework for quantum computing.
\bibitem{{azmqos}} AZM-QOS generated workflow artifacts and reports.
\end{{thebibliography}}

\end{{document}}
"""
    output_path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return output_path


def make_thesis_appendix_scaffold(project_name: str, artifacts: dict[str, str], output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Thesis Appendix Scaffold: AZM-QOS END/VQS + QEC Workflow",
        "",
        f"Project: `{project_name}`",
        "",
        "## Appendix A: Reproducibility Commands",
        "",
        "See `final_command_summary.md`.",
        "",
        "## Appendix B: Version Lockfile",
        "",
        "See `version_lockfile.json`.",
        "",
        "## Appendix C: Hardware-Analysis Artifacts",
        "",
    ]
    for key, value in artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    lines.extend([
        "",
        "## Appendix D: Notes",
        "",
        "Synthetic fallback records are not hardware evidence. They are included for workflow validation and software testing.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_final_command_summary(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = r"""
# Final AZM-QOS v4.8 Command Summary

## Install

```powershell
python -m pip install -e .
```

## Required first command

```powershell
azmqos production-init --output-dir outputs\production_project --project-name my_endvqs_project
```

## Plan

```powershell
azmqos production-plan --config outputs\production_project\azmqos_production.json
```

## Stable integrated platform

```powershell
azmqos stable-run --config outputs\production_project\azmqos_production.json --backend fallback --max-components 2 --shots 64
```

## QEC hardware analysis

```powershell
azmqos production-hardware-analysis --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```

## Final export

```powershell
azmqos production-final-export --config outputs\production_project\azmqos_production.json --backend-name ibm_fez --code repetition3 --max-components 2 --shots 64 --rounds 3
```
"""
    output_path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")
    return output_path


def make_reproducibility_checklist(project_name: str, artifacts: dict[str, str]) -> ReproducibilityChecklist:
    items = {
        "hardware_analysis_report_exists": Path(artifacts.get("hardware_analysis_report", "")).exists(),
        "run_summary_exists": Path(artifacts.get("run_summary_json", "")).exists(),
        "calibration_metadata_exists": Path(artifacts.get("calibration_metadata_json", "")).exists(),
        "counts_confidence_intervals_exists": Path(artifacts.get("counts_confidence_intervals_csv", "")).exists(),
        "failure_bands_exists": Path(artifacts.get("logical_failure_bands_csv", "")).exists(),
        "figures_generated": Path(artifacts.get("figures_dir", "")).exists(),
        "manuscript_scaffold_exists": Path(artifacts.get("latex_manuscript", "")).exists(),
        "thesis_appendix_exists": Path(artifacts.get("thesis_appendix", "")).exists(),
        "version_lockfile_exists": Path(artifacts.get("version_lockfile", "")).exists(),
        "command_summary_exists": Path(artifacts.get("final_command_summary", "")).exists(),
    }
    notes = []
    if not all(items.values()):
        notes.append("Some optional export artifacts are missing. Check paths in final_export_manifest.json.")
    return ReproducibilityChecklist(project_name=project_name, items=items, notes=notes)


def export_reproducibility_checklist(checklist: ReproducibilityChecklist, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Reproducibility Checklist", "", f"Project: `{checklist.project_name}`", ""]
    for key, value in checklist.items.items():
        mark = "✅" if value else "❌"
        lines.append(f"- {mark} **{key}**")
    if checklist.notes:
        lines.extend(["", "## Notes", ""])
        for note in checklist.notes:
            lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def make_version_lockfile(package_root, artifacts: dict[str, str]) -> VersionLockfile:
    package_root = Path(package_root)
    important = {}
    for name in ["pyproject.toml", "README.md"]:
        p = package_root / name
        if p.exists():
            important[name] = str(p)
    for key in ["hardware_analysis_report", "latex_manuscript", "thesis_appendix"]:
        if key in artifacts:
            important[key] = artifacts[key]
    return VersionLockfile(
        package_version=read_package_version(package_root),
        python_version=sys.version,
        platform=platform.platform(),
        created_at_unix=time.time(),
        important_files=important,
        installed_packages_hint=[
            "qiskit",
            "qiskit-aer",
            "qiskit-ibm-runtime",
            "matplotlib",
            "numpy",
        ],
    )


def export_version_lockfile(lockfile: VersionLockfile, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(lockfile), indent=2, default=_json_default), encoding="utf-8")
    return path


def make_final_export_report(result: FinalExportResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.8 Final Export Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Figures",
        "",
    ]
    for fig in result.figures:
        lines.extend(["```text", fig.summary(), "```", ""])
    lines.extend([
        "## Checklist",
        "",
        "```text",
        result.checklist.summary(),
        "```",
        "",
        "## Lockfile",
        "",
        "```text",
        result.lockfile.summary(),
        "```",
        "",
    ])
    if result.warnings:
        lines.extend(["## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    lines.extend(["## Artifacts", ""])
    for key, value in result.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    lines.extend([
        "",
        "## Note",
        "",
        "This final export is a manuscript/thesis and reproducibility packaging layer. Synthetic-only results remain workflow validation rather than hardware evidence.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def create_final_project_archive(source_dir, archive_path):
    source_dir = Path(source_dir)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in source_dir.rglob("*"):
            if path.is_file() and path.resolve() != archive_path.resolve():
                z.write(path, arcname=path.relative_to(source_dir))
    return archive_path


def export_json_dataclasses(items, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(items, list):
        payload = [asdict(x) for x in items]
    else:
        payload = asdict(items)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
    return path


def run_final_export_from_analysis(
    analysis: HardwareAnalysisResult,
    output_dir,
    package_root: str | Path | None = None,
) -> FinalExportResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_root = Path(package_root) if package_root else Path(__file__).resolve().parents[1]

    final_artifacts = {}
    final_artifacts.update(analysis.artifacts)
    final_artifacts["figures_dir"] = str(output_dir / "figures")

    figures = copy_final_figures(analysis, output_dir)
    summary_fig = make_summary_figure_from_artifacts(analysis, output_dir)
    if summary_fig:
        figures.append(summary_fig)

    final_artifacts["latex_manuscript"] = str(make_latex_manuscript_scaffold(
        analysis.project_name,
        figures,
        output_dir / "manuscript" / "azmqos_manuscript_scaffold.tex",
    ))
    final_artifacts["thesis_appendix"] = str(make_thesis_appendix_scaffold(
        analysis.project_name,
        final_artifacts,
        output_dir / "thesis" / "azmqos_thesis_appendix.md",
    ))
    final_artifacts["final_command_summary"] = str(make_final_command_summary(output_dir / "final_command_summary.md"))

    lockfile = make_version_lockfile(package_root, final_artifacts)
    final_artifacts["version_lockfile"] = str(export_version_lockfile(lockfile, output_dir / "version_lockfile.json"))

    checklist = make_reproducibility_checklist(analysis.project_name, final_artifacts)
    final_artifacts["reproducibility_checklist"] = str(export_reproducibility_checklist(checklist, output_dir / "reproducibility_checklist.md"))
    final_artifacts["figures_manifest"] = str(export_json_dataclasses(figures, output_dir / "figures" / "figures_manifest.json"))

    warnings = list(analysis.warnings)
    if analysis.run_summary.runtime_records == 0:
        warnings.append("Final export contains no real Runtime records; manuscript must label results as synthetic workflow validation.")

    result = FinalExportResult(
        project_name=analysis.project_name,
        output_dir=str(output_dir),
        figures=figures,
        checklist=checklist,
        lockfile=lockfile,
        artifacts=final_artifacts,
        warnings=warnings,
        metadata={"analysis_summary": analysis.summary()},
    )

    final_artifacts["final_export_report"] = str(make_final_export_report(result, output_dir / "final_export_report.md"))

    manifest_path = output_dir / "final_export_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.8 final manuscript/thesis export",
        "summary": result.summary(),
        "warnings": warnings,
        "artifacts": final_artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    final_artifacts["manifest"] = str(manifest_path)

    archive_path = create_final_project_archive(output_dir, output_dir / "archives" / f"{analysis.project_name}_v4_8_final_export_archive.zip")
    final_artifacts["final_export_archive"] = str(archive_path)

    return FinalExportResult(
        project_name=analysis.project_name,
        output_dir=str(output_dir),
        figures=figures,
        checklist=checklist,
        lockfile=lockfile,
        artifacts=final_artifacts,
        warnings=warnings,
        metadata={"analysis_summary": analysis.summary()},
    )


def run_final_export_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = run_hardware_analysis_demo(output_dir / "analysis_base", backend_name="ibm_fez", rounds=1, shots=32)
    return run_final_export_from_analysis(analysis, output_dir / "final_export")


def run_production_final_export(
    spec_or_path,
    backend_name: str = "ibm_fez",
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    rounds: int = 3,
    job_ids_file: str | None = None,
    enable_runtime_fetch: bool = False,
    force_refresh: bool = False,
    calibration_file: str | None = None,
    physical_error_rate: float = 0.01,
    measurement_error_rate: float = 0.02,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    analysis = run_production_hardware_analysis(
        spec,
        backend_name=backend_name,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        rounds=rounds,
        job_ids_file=job_ids_file,
        enable_runtime_fetch=enable_runtime_fetch,
        force_refresh=force_refresh,
        calibration_file=calibration_file,
        physical_error_rate=physical_error_rate,
        measurement_error_rate=measurement_error_rate,
    )
    output_dir = Path(spec.output_dir) / "final_export"
    return run_final_export_from_analysis(analysis, output_dir)
