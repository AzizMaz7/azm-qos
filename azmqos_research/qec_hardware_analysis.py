from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import json
import math
import time
import zipfile

from .production import load_production_spec
from .qec_hardware import default_backend_target, BackendTargetSpec
from .qec_runtime_fetch import (
    RuntimeSyncResult,
    RuntimeFetchRecord,
    run_runtime_fetch_demo,
    run_production_runtime_sync,
)
from .qec_hardware_sync import HardwareCountsRecord, HardwareSyncComparison
from .experiment_db import (
    ExperimentDatabase,
    BackendMetadataRecord,
    new_run_record,
    artifact_from_path,
    export_run_table_csv,
    export_dashboard_json,
    make_run_database_report,
)
from .dashboard import build_dashboard_package


@dataclass
class BackendCalibrationMetadata:
    backend_name: str
    calibration_timestamp_unix: float
    source: str = "synthetic_or_imported"
    median_readout_error: float = 0.02
    median_cx_error: float = 0.015
    median_t1_us: float = 150.0
    median_t2_us: float = 120.0
    n_qubits: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "BackendCalibrationMetadata\n"
            f"  backend_name: {self.backend_name}\n"
            f"  source: {self.source}\n"
            f"  median_readout_error: {self.median_readout_error}\n"
            f"  median_cx_error: {self.median_cx_error}\n"
            f"  median_t1_us: {self.median_t1_us}\n"
            f"  median_t2_us: {self.median_t2_us}\n"
            f"  n_qubits: {self.n_qubits}"
        )


@dataclass
class HardwareRunSummary:
    project_name: str
    backend_name: str
    total_records: int
    runtime_records: int
    synthetic_records: int
    cached_records: int
    passed_consistency: int
    failed_consistency: int
    mean_total_variation_distance: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "HardwareRunSummary\n"
            f"  project: {self.project_name}\n"
            f"  backend: {self.backend_name}\n"
            f"  total_records: {self.total_records}\n"
            f"  runtime_records: {self.runtime_records}\n"
            f"  synthetic_records: {self.synthetic_records}\n"
            f"  cached_records: {self.cached_records}\n"
            f"  passed_consistency: {self.passed_consistency}\n"
            f"  failed_consistency: {self.failed_consistency}\n"
            f"  mean_tvd: {self.mean_total_variation_distance:.8f}"
        )


@dataclass
class CountsConfidenceInterval:
    job_id: str
    circuit_id: str
    outcome: str
    count: int
    shots: int
    probability: float
    lower_95: float
    upper_95: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "CountsConfidenceInterval\n"
            f"  job_id: {self.job_id}\n"
            f"  circuit: {self.circuit_id}\n"
            f"  outcome: {self.outcome}\n"
            f"  probability: {self.probability:.8f}\n"
            f"  ci95: [{self.lower_95:.8f}, {self.upper_95:.8f}]\n"
            f"  source: {self.source}"
        )


@dataclass
class LogicalFailureConfidenceBand:
    label: str
    failure_rate: float
    shots: int
    lower_95: float
    upper_95: float
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "LogicalFailureConfidenceBand\n"
            f"  label: {self.label}\n"
            f"  failure_rate: {self.failure_rate:.8f}\n"
            f"  ci95: [{self.lower_95:.8f}, {self.upper_95:.8f}]\n"
            f"  shots: {self.shots}\n"
            f"  source: {self.source}"
        )


@dataclass
class HardwareAnalysisResult:
    project_name: str
    backend: BackendTargetSpec
    calibration: BackendCalibrationMetadata
    run_summary: HardwareRunSummary
    count_intervals: list[CountsConfidenceInterval]
    failure_bands: list[LogicalFailureConfidenceBand]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "HardwareAnalysisResult\n"
            f"  project: {self.project_name}\n"
            f"  backend: {self.backend.backend_name}\n"
            f"  count_intervals: {len(self.count_intervals)}\n"
            f"  failure_bands: {len(self.failure_bands)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def wilson_interval(count: int, shots: int, z: float = 1.96) -> tuple[float, float, float]:
    if shots <= 0:
        return 0.0, 0.0, 0.0
    p = count / shots
    denom = 1.0 + z * z / shots
    center = (p + z * z / (2 * shots)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * shots)) / shots) / denom
    return p, max(0.0, center - half), min(1.0, center + half)


def load_backend_calibration(path, backend_name: str = "ibm_fez") -> BackendCalibrationMetadata:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return BackendCalibrationMetadata(
        backend_name=str(data.get("backend_name", backend_name)),
        calibration_timestamp_unix=float(data.get("calibration_timestamp_unix", time.time())),
        source=str(data.get("source", "imported")),
        median_readout_error=float(data.get("median_readout_error", 0.02)),
        median_cx_error=float(data.get("median_cx_error", 0.015)),
        median_t1_us=float(data.get("median_t1_us", 150.0)),
        median_t2_us=float(data.get("median_t2_us", 120.0)),
        n_qubits=data.get("n_qubits"),
        metadata=dict(data.get("metadata", {})),
    )


def default_calibration_metadata(backend_name: str = "ibm_fez") -> BackendCalibrationMetadata:
    backend = default_backend_target(backend_name)
    return BackendCalibrationMetadata(
        backend_name=backend_name,
        calibration_timestamp_unix=time.time(),
        source="synthetic_default",
        median_readout_error=0.02,
        median_cx_error=0.015,
        median_t1_us=150.0,
        median_t2_us=120.0,
        n_qubits=backend.max_qubits,
        metadata={"note": "Synthetic calibration metadata scaffold."},
    )


def classify_fetch_source(record: RuntimeFetchRecord) -> str:
    if record.source == "runtime":
        return "runtime"
    if "synthetic" in record.source:
        return "synthetic"
    if record.cached and "synthetic" in record.source:
        return "synthetic_cached"
    return record.source or "unknown"


def make_hardware_run_summary(project_name: str, backend_name: str, runtime_result: RuntimeSyncResult) -> HardwareRunSummary:
    total = len(runtime_result.fetch_records)
    runtime_records = sum(1 for r in runtime_result.fetch_records if classify_fetch_source(r) == "runtime")
    synthetic_records = sum(1 for r in runtime_result.fetch_records if "synthetic" in classify_fetch_source(r))
    cached_records = sum(1 for r in runtime_result.fetch_records if r.cached)
    passed = sum(1 for c in runtime_result.comparisons if c.passed_consistency_check)
    failed = len(runtime_result.comparisons) - passed
    mean_tvd = sum(c.total_variation_distance for c in runtime_result.comparisons) / max(1, len(runtime_result.comparisons))
    return HardwareRunSummary(
        project_name=project_name,
        backend_name=backend_name,
        total_records=total,
        runtime_records=runtime_records,
        synthetic_records=synthetic_records,
        cached_records=cached_records,
        passed_consistency=passed,
        failed_consistency=failed,
        mean_total_variation_distance=mean_tvd,
        metadata={"runtime_result_summary": runtime_result.summary()},
    )


def make_counts_confidence_intervals(fetch_records: list[RuntimeFetchRecord]) -> list[CountsConfidenceInterval]:
    intervals = []
    for record in fetch_records:
        source = classify_fetch_source(record)
        counts = record.counts_record.counts
        shots = record.counts_record.shots or sum(counts.values())
        for outcome, count in sorted(counts.items()):
            p, lo, hi = wilson_interval(int(count), int(shots))
            intervals.append(
                CountsConfidenceInterval(
                    job_id=record.job_reference.job_id,
                    circuit_id=record.job_reference.circuit_id,
                    outcome=str(outcome),
                    count=int(count),
                    shots=int(shots),
                    probability=p,
                    lower_95=lo,
                    upper_95=hi,
                    source=source,
                    metadata={"backend_name": record.job_reference.backend_name},
                )
            )
    return intervals


def make_failure_bands_from_comparisons(comparisons: list[HardwareSyncComparison], source: str = "sync_comparison") -> list[LogicalFailureConfidenceBand]:
    bands = []
    for comp in comparisons:
        # Treat TVD as a conservative failure proxy for scaffold analysis.
        failures = int(round(comp.total_variation_distance * comp.shots))
        p, lo, hi = wilson_interval(failures, max(1, comp.shots))
        bands.append(
            LogicalFailureConfidenceBand(
                label=comp.circuit_id,
                failure_rate=p,
                shots=comp.shots,
                lower_95=lo,
                upper_95=hi,
                source=source,
                metadata={"job_id": comp.job_id, "backend_name": comp.backend_name},
            )
        )
    return bands


def export_run_summary_json(summary: HardwareRunSummary, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(summary), indent=2, default=_json_default), encoding="utf-8")
    return path


def export_calibration_json(calibration: BackendCalibrationMetadata, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(calibration), indent=2, default=_json_default), encoding="utf-8")
    return path


def export_counts_intervals_csv(intervals: list[CountsConfidenceInterval], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["job_id", "circuit_id", "outcome", "count", "shots", "probability", "lower_95", "upper_95", "source"])
        for x in intervals:
            writer.writerow([x.job_id, x.circuit_id, x.outcome, x.count, x.shots, x.probability, x.lower_95, x.upper_95, x.source])
    return path


def export_failure_bands_csv(bands: list[LogicalFailureConfidenceBand], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "failure_rate", "shots", "lower_95", "upper_95", "source"])
        for x in bands:
            writer.writerow([x.label, x.failure_rate, x.shots, x.lower_95, x.upper_95, x.source])
    return path


def export_json_dataclasses(items, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(items, list):
        payload = [asdict(x) for x in items]
    else:
        payload = asdict(items)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
    return path


def plot_failure_bands(bands: list[LogicalFailureConfidenceBand], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(x.summary() for x in bands), encoding="utf-8")
        return txt

    labels = [x.label for x in bands]
    y = [x.failure_rate for x in bands]
    lower = [x.failure_rate - x.lower_95 for x in bands]
    upper = [x.upper_95 - x.failure_rate for x in bands]
    xvals = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.errorbar(xvals, y, yerr=[lower, upper], fmt="o")
    ax.set_xlabel("circuit")
    ax.set_ylabel("logical failure proxy")
    ax.set_title("Logical failure-rate confidence bands")
    if len(labels) <= 12:
        ax.set_xticks(xvals)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def plot_real_vs_synthetic_summary(summary: HardwareRunSummary, path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text(summary.summary(), encoding="utf-8")
        return txt

    labels = ["runtime", "synthetic", "cached"]
    values = [summary.runtime_records, summary.synthetic_records, summary.cached_records]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(labels, values)
    ax.set_ylabel("records")
    ax.set_title("Hardware result source separation")
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def make_hardware_analysis_report(result: HardwareAnalysisResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.7 Hardware Analysis Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Hardware run summary",
        "",
        "```text",
        result.run_summary.summary(),
        "```",
        "",
        "## Calibration metadata",
        "",
        "```text",
        result.calibration.summary(),
        "```",
        "",
        "## Count confidence intervals",
        "",
    ]
    for item in result.count_intervals[:20]:
        lines.extend(["```text", item.summary(), "```", ""])
    if len(result.count_intervals) > 20:
        lines.append(f"... truncated in report; full table has {len(result.count_intervals)} rows.")
        lines.append("")
    lines.extend(["## Logical failure confidence bands", ""])
    for item in result.failure_bands:
        lines.extend(["```text", item.summary(), "```", ""])
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
        "## Scientific note",
        "",
        "v4.7 separates real Runtime records from synthetic fallback records. Treat synthetic-only analyses as workflow validation, not hardware evidence.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def attach_hardware_analysis_to_database(spec, result: HardwareAnalysisResult, database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    artifacts = [
        artifact_from_path(path, name=name, artifact_type="hardware_analysis_artifact")
        for name, path in artifact_paths.items()
    ]
    record = new_run_record(
        name=f"hardware_analysis_{result.project_name}",
        run_type="qec_hardware_analysis",
        status="completed",
        tags=["qec", "hardware_analysis", result.backend.backend_name],
        parameters={
            "project_name": result.project_name,
            "backend_name": result.backend.backend_name,
            "calibration_source": result.calibration.source,
            "total_records": result.run_summary.total_records,
        },
        metrics={
            "runtime_records": float(result.run_summary.runtime_records),
            "synthetic_records": float(result.run_summary.synthetic_records),
            "cached_records": float(result.run_summary.cached_records),
            "passed_consistency": float(result.run_summary.passed_consistency),
            "failed_consistency": float(result.run_summary.failed_consistency),
            "mean_total_variation_distance": result.run_summary.mean_total_variation_distance,
        },
        backend=BackendMetadataRecord(
            backend_name=result.backend.backend_name,
            job_status="ANALYSIS_COMPLETED",
            timestamp_unix=time.time(),
        ),
        artifacts=artifacts,
        notes="Hardware-analysis report with real-vs-synthetic separation and confidence intervals.",
    )
    db.append(record)
    return db, [record]


def create_final_qec_experiment_archive(output_dir, archive_path):
    output_dir = Path(output_dir)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in output_dir.rglob("*"):
            if path.is_file() and path.resolve() != archive_path.resolve():
                z.write(path, arcname=path.relative_to(output_dir))
    return archive_path


def analyze_runtime_sync_result(
    runtime_result: RuntimeSyncResult,
    output_dir,
    calibration_file: str | None = None,
) -> HardwareAnalysisResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    backend = runtime_result.backend
    calibration = load_backend_calibration(calibration_file, backend_name=backend.backend_name) if calibration_file else default_calibration_metadata(backend.backend_name)
    run_summary = make_hardware_run_summary(runtime_result.project_name, backend.backend_name, runtime_result)
    count_intervals = make_counts_confidence_intervals(runtime_result.fetch_records)
    failure_bands = make_failure_bands_from_comparisons(runtime_result.comparisons)

    artifacts = {}
    artifacts["run_summary_json"] = str(export_run_summary_json(run_summary, output_dir / "hardware_run_summary.json"))
    artifacts["calibration_metadata_json"] = str(export_calibration_json(calibration, output_dir / "calibration_metadata.json"))
    artifacts["counts_confidence_intervals_csv"] = str(export_counts_intervals_csv(count_intervals, output_dir / "counts_confidence_intervals.csv"))
    artifacts["counts_confidence_intervals_json"] = str(export_json_dataclasses(count_intervals, output_dir / "counts_confidence_intervals.json"))
    artifacts["logical_failure_bands_csv"] = str(export_failure_bands_csv(failure_bands, output_dir / "logical_failure_bands.csv"))
    artifacts["logical_failure_bands_json"] = str(export_json_dataclasses(failure_bands, output_dir / "logical_failure_bands.json"))
    artifacts["failure_bands_figure"] = str(plot_failure_bands(failure_bands, output_dir / "logical_failure_bands.png"))
    artifacts["source_separation_figure"] = str(plot_real_vs_synthetic_summary(run_summary, output_dir / "real_vs_synthetic_summary.png"))

    warnings = list(runtime_result.warnings)
    if run_summary.runtime_records == 0:
        warnings.append("No real Runtime records detected; this analysis is synthetic/fallback only.")

    result = HardwareAnalysisResult(
        project_name=runtime_result.project_name,
        backend=backend,
        calibration=calibration,
        run_summary=run_summary,
        count_intervals=count_intervals,
        failure_bands=failure_bands,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"runtime_artifacts": runtime_result.artifacts},
    )
    artifacts["hardware_analysis_report"] = str(make_hardware_analysis_report(result, output_dir / "hardware_analysis_report.md"))

    manifest_path = output_dir / "hardware_analysis_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.7 hardware analysis",
        "summary": result.summary(),
        "warnings": warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    archive_path = create_final_qec_experiment_archive(output_dir, output_dir / "archives" / f"{runtime_result.project_name}_qec_experiment_archive.zip")
    artifacts["final_qec_experiment_archive"] = str(archive_path)

    return HardwareAnalysisResult(
        project_name=runtime_result.project_name,
        backend=backend,
        calibration=calibration,
        run_summary=run_summary,
        count_intervals=count_intervals,
        failure_bands=failure_bands,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"runtime_artifacts": runtime_result.artifacts},
    )


def run_hardware_analysis_demo(output_dir, backend_name: str = "ibm_fez", rounds: int = 2, shots: int = 64):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_result = run_runtime_fetch_demo(output_dir / "runtime_fetch_base", backend_name=backend_name, rounds=rounds, shots=shots)
    result = analyze_runtime_sync_result(runtime_result, output_dir / "hardware_analysis")

    return result


def run_production_hardware_analysis(
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
    output_dir = Path(spec.output_dir) / "hardware_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    runtime_result = run_production_runtime_sync(
        spec,
        backend_name=backend_name,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        rounds=rounds,
        job_ids_file=job_ids_file,
        enable_runtime_fetch=enable_runtime_fetch,
        force_refresh=force_refresh,
        physical_error_rate=physical_error_rate,
        measurement_error_rate=measurement_error_rate,
    )
    result = analyze_runtime_sync_result(runtime_result, output_dir, calibration_file=calibration_file)

    db, records = attach_hardware_analysis_to_database(
        spec=spec,
        result=result,
        database_path=Path(spec.output_dir) / "database" / "hardware_analysis.jsonl",
        artifact_paths={
            "hardware_analysis_report": result.artifacts["hardware_analysis_report"],
            "counts_confidence_intervals_csv": result.artifacts["counts_confidence_intervals_csv"],
            "logical_failure_bands_csv": result.artifacts["logical_failure_bands_csv"],
            "final_qec_experiment_archive": result.artifacts["final_qec_experiment_archive"],
        },
    )
    result.artifacts["hardware_analysis_database_jsonl"] = str(db.path)
    result.artifacts["hardware_analysis_run_table_csv"] = str(export_run_table_csv(records, Path(spec.output_dir) / "database" / "hardware_analysis_run_table.csv"))
    result.artifacts["hardware_analysis_dashboard_json"] = str(export_dashboard_json(records, Path(spec.output_dir) / "database" / "hardware_analysis_dashboard.json"))
    result.artifacts["hardware_analysis_database_report"] = str(make_run_database_report(records, Path(spec.output_dir) / "database" / "hardware_analysis_database_report.md"))

    dashboard = build_dashboard_package(Path(spec.output_dir) / "dashboard_hardware_analysis", database_path=db.path)
    result.artifacts["hardware_analysis_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    result.artifacts["hardware_analysis_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")

    # Refresh report and manifest after adding DB/dashboard artifacts.
    result.artifacts["hardware_analysis_report"] = str(make_hardware_analysis_report(result, output_dir / "hardware_analysis_report.md"))
    manifest_path = output_dir / "production_hardware_analysis_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.7 production hardware analysis",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": result.warnings,
        "artifacts": result.artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    result.artifacts["manifest"] = str(manifest_path)

    archive_path = create_final_qec_experiment_archive(Path(spec.output_dir), Path(spec.output_dir) / "archives" / f"{spec.project_name}_v4_7_final_qec_experiment_archive.zip")
    result.artifacts["production_final_qec_experiment_archive"] = str(archive_path)

    return result
