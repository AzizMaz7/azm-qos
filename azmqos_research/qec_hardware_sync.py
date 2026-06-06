from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import time

from .production import load_production_spec
from .qec_hardware import (
    BackendTargetSpec,
    HardwareDryRunJobManifest,
    ProductionQECHardwareResult,
    default_backend_target,
    run_production_qec_hardware_dry_run,
    run_qec_hardware_demo,
)
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
class HardwareJobReference:
    job_id: str
    backend_name: str
    circuit_id: str
    shots: int
    dry_run_job_id: str | None = None
    source: str = "manual_or_dry_run"
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "HardwareJobReference\n"
            f"  job_id: {self.job_id}\n"
            f"  backend: {self.backend_name}\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  shots: {self.shots}\n"
            f"  dry_run_job_id: {self.dry_run_job_id}\n"
            f"  source: {self.source}"
        )


@dataclass
class HardwareCountsRecord:
    job_id: str
    backend_name: str
    circuit_id: str
    counts: dict[str, int]
    shots: int
    status: str = "SYNCED"
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "HardwareCountsRecord\n"
            f"  job_id: {self.job_id}\n"
            f"  backend: {self.backend_name}\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  shots: {self.shots}\n"
            f"  status: {self.status}\n"
            f"  outcomes: {len(self.counts)}"
        )


@dataclass
class HardwareSyncComparison:
    job_id: str
    circuit_id: str
    backend_name: str
    dry_run_status: str
    hardware_status: str
    shots: int
    total_variation_distance: float
    dominant_dry_run_outcome: str
    dominant_hardware_outcome: str
    passed_consistency_check: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "HardwareSyncComparison\n"
            f"  job_id: {self.job_id}\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  backend: {self.backend_name}\n"
            f"  tvd: {self.total_variation_distance:.8f}\n"
            f"  dry_dominant: {self.dominant_dry_run_outcome}\n"
            f"  hw_dominant: {self.dominant_hardware_outcome}\n"
            f"  passed: {self.passed_consistency_check}"
        )


@dataclass
class ProductionHardwareSyncResult:
    project_name: str
    backend: BackendTargetSpec
    job_references: list[HardwareJobReference]
    counts_records: list[HardwareCountsRecord]
    comparisons: list[HardwareSyncComparison]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        passed = sum(1 for x in self.comparisons if x.passed_consistency_check)
        return (
            "ProductionHardwareSyncResult\n"
            f"  project: {self.project_name}\n"
            f"  backend: {self.backend.backend_name}\n"
            f"  job_references: {len(self.job_references)}\n"
            f"  counts_records: {len(self.counts_records)}\n"
            f"  comparisons: {len(self.comparisons)}\n"
            f"  consistency_passed: {passed}/{len(self.comparisons)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def _stable_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    intval = int(digest[:14], 16)
    return intval / float(16 ** 14 - 1)


def normalize_counts(counts: dict[str, int], n_bits: int | None = None) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, value in counts.items():
        bitstring = str(key).replace(" ", "")
        bitstring = bitstring.split()[-1] if " " in bitstring else bitstring
        if n_bits is not None:
            if len(bitstring) < n_bits:
                bitstring = bitstring.zfill(n_bits)
            elif len(bitstring) > n_bits:
                bitstring = bitstring[-n_bits:]
        out[bitstring] = out.get(bitstring, 0) + int(value)
    return out


def counts_to_probabilities(counts: dict[str, int]) -> dict[str, float]:
    shots = sum(int(v) for v in counts.values())
    if shots <= 0:
        return {}
    return {str(k): int(v) / shots for k, v in counts.items()}


def total_variation_distance(a: dict[str, int], b: dict[str, int]) -> float:
    pa = counts_to_probabilities(a)
    pb = counts_to_probabilities(b)
    keys = set(pa) | set(pb)
    return 0.5 * sum(abs(pa.get(k, 0.0) - pb.get(k, 0.0)) for k in keys)


def dominant_outcome(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    return max(counts.items(), key=lambda kv: (int(kv[1]), str(kv[0])))[0]


def job_reference_from_manifest(manifest: HardwareDryRunJobManifest, real_job_id: str | None = None) -> HardwareJobReference:
    job_id = real_job_id or manifest.job_id.replace("DRYRUN", "SYNC")
    return HardwareJobReference(
        job_id=job_id,
        backend_name=manifest.backend_name,
        circuit_id=manifest.circuit_id,
        shots=manifest.shots,
        dry_run_job_id=manifest.job_id,
        source="dry_run_manifest",
        metadata={"dry_run_status": manifest.status},
    )


def job_references_from_manifests(manifests: list[HardwareDryRunJobManifest]) -> list[HardwareJobReference]:
    return [job_reference_from_manifest(m) for m in manifests]


def parse_job_ids_file(path, backend_name: str = "ibm_fez", default_shots: int = 1024) -> list[HardwareJobReference]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Job IDs file not found: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("jobs", data if isinstance(data, list) else [])
        refs = []
        for i, item in enumerate(items):
            if isinstance(item, str):
                refs.append(HardwareJobReference(job_id=item, backend_name=backend_name, circuit_id=f"manual_circuit_{i}", shots=default_shots, source="job_ids_file"))
            else:
                refs.append(HardwareJobReference(
                    job_id=str(item.get("job_id")),
                    backend_name=str(item.get("backend_name", backend_name)),
                    circuit_id=str(item.get("circuit_id", f"manual_circuit_{i}")),
                    shots=int(item.get("shots", default_shots)),
                    dry_run_job_id=item.get("dry_run_job_id"),
                    source="job_ids_file",
                    metadata=dict(item.get("metadata", {})),
                ))
        return refs

    refs = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            job_id = line.strip()
            if job_id:
                refs.append(HardwareJobReference(job_id=job_id, backend_name=backend_name, circuit_id=f"manual_circuit_{i}", shots=default_shots, source="job_ids_file"))
    return refs


def synthetic_hardware_counts_for_job(job: HardwareJobReference, n_bits: int = 1, bias: float = 0.05) -> HardwareCountsRecord:
    # Deterministic fallback for sync workflow testing. Outcome 0 dominates unless the job hash pushes noise high.
    shots = int(job.shots)
    u = _stable_unit_interval(f"{job.job_id}|{job.circuit_id}|hardware_counts")
    p_one = max(0.0, min(1.0, bias + 0.1 * u))
    one = int(round(shots * p_one))
    zero = shots - one
    zero_key = "0" * n_bits
    one_key = ("0" * (n_bits - 1)) + "1" if n_bits > 1 else "1"
    counts = {zero_key: zero, one_key: one}
    return HardwareCountsRecord(
        job_id=job.job_id,
        backend_name=job.backend_name,
        circuit_id=job.circuit_id,
        counts=counts,
        shots=shots,
        status="SYNTHETIC_SYNCED",
        metadata={"synthetic": True, "bias": bias},
    )


def parse_counts_file(path) -> list[HardwareCountsRecord]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Counts file not found: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("counts_records", data if isinstance(data, list) else [])
        out = []
        for item in items:
            counts = normalize_counts(dict(item.get("counts", {})))
            shots = int(item.get("shots", sum(counts.values())))
            out.append(HardwareCountsRecord(
                job_id=str(item.get("job_id")),
                backend_name=str(item.get("backend_name", "")),
                circuit_id=str(item.get("circuit_id", "")),
                counts=counts,
                shots=shots,
                status=str(item.get("status", "IMPORTED")),
                metadata=dict(item.get("metadata", {})),
            ))
        return out

    # CSV columns: job_id,backend_name,circuit_id,counts_json,shots,status
    out = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            counts = normalize_counts(json.loads(row.get("counts_json", "{}")))
            shots = int(row.get("shots") or sum(counts.values()))
            out.append(HardwareCountsRecord(
                job_id=row.get("job_id", ""),
                backend_name=row.get("backend_name", ""),
                circuit_id=row.get("circuit_id", ""),
                counts=counts,
                shots=shots,
                status=row.get("status", "IMPORTED"),
            ))
    return out


def expected_dry_run_counts(job: HardwareJobReference, n_bits: int = 1) -> dict[str, int]:
    zero_key = "0" * n_bits
    one_key = ("0" * (n_bits - 1)) + "1" if n_bits > 1 else "1"
    # Dry-run expected distribution is ideal/no-error dominant zero.
    return {zero_key: int(round(0.95 * job.shots)), one_key: job.shots - int(round(0.95 * job.shots))}


def compare_dry_run_to_hardware(
    job: HardwareJobReference,
    record: HardwareCountsRecord,
    tolerance: float = 0.25,
    n_bits: int = 1,
) -> HardwareSyncComparison:
    dry_counts = expected_dry_run_counts(job, n_bits=n_bits)
    hw_counts = normalize_counts(record.counts, n_bits=n_bits)
    tvd = total_variation_distance(dry_counts, hw_counts)
    return HardwareSyncComparison(
        job_id=job.job_id,
        circuit_id=job.circuit_id,
        backend_name=job.backend_name,
        dry_run_status=str(job.metadata.get("dry_run_status", "DRY_RUN_READY")),
        hardware_status=record.status,
        shots=record.shots,
        total_variation_distance=tvd,
        dominant_dry_run_outcome=dominant_outcome(dry_counts),
        dominant_hardware_outcome=dominant_outcome(hw_counts),
        passed_consistency_check=tvd <= tolerance,
        metadata={
            "tolerance": tolerance,
            "dry_counts": dry_counts,
            "hardware_counts": hw_counts,
        },
    )


def sync_hardware_results(
    job_references: list[HardwareJobReference],
    counts_records: list[HardwareCountsRecord] | None = None,
    n_bits: int = 1,
    tolerance: float = 0.25,
) -> tuple[list[HardwareCountsRecord], list[HardwareSyncComparison]]:
    if counts_records is None:
        counts_records = [synthetic_hardware_counts_for_job(job, n_bits=n_bits) for job in job_references]

    counts_by_job = {record.job_id: record for record in counts_records}
    synced_records = []
    comparisons = []
    for job in job_references:
        record = counts_by_job.get(job.job_id)
        if record is None:
            record = synthetic_hardware_counts_for_job(job, n_bits=n_bits)
        synced_records.append(record)
        comparisons.append(compare_dry_run_to_hardware(job, record, tolerance=tolerance, n_bits=n_bits))
    return synced_records, comparisons


def export_job_references_csv(items: list[HardwareJobReference], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["job_id", "backend_name", "circuit_id", "shots", "dry_run_job_id", "source"])
        for x in items:
            writer.writerow([x.job_id, x.backend_name, x.circuit_id, x.shots, x.dry_run_job_id, x.source])
    return path


def export_counts_records_csv(items: list[HardwareCountsRecord], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["job_id", "backend_name", "circuit_id", "shots", "status", "counts_json"])
        for x in items:
            writer.writerow([x.job_id, x.backend_name, x.circuit_id, x.shots, x.status, json.dumps(x.counts)])
    return path


def export_sync_comparisons_csv(items: list[HardwareSyncComparison], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "job_id", "circuit_id", "backend_name", "dry_run_status", "hardware_status", "shots",
            "total_variation_distance", "dominant_dry_run_outcome", "dominant_hardware_outcome",
            "passed_consistency_check"
        ])
        for x in items:
            writer.writerow([
                x.job_id, x.circuit_id, x.backend_name, x.dry_run_status, x.hardware_status, x.shots,
                x.total_variation_distance, x.dominant_dry_run_outcome, x.dominant_hardware_outcome,
                x.passed_consistency_check,
            ])
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


def plot_sync_comparisons(items: list[HardwareSyncComparison], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(x.summary() for x in items), encoding="utf-8")
        return txt

    labels = [x.circuit_id for x in items]
    tvd = [x.total_variation_distance for x in items]
    xvals = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(xvals, tvd, marker="o")
    ax.set_xlabel("circuit")
    ax.set_ylabel("total variation distance")
    ax.set_title("Dry-run vs hardware-style counts comparison")
    if len(labels) <= 12:
        ax.set_xticks(xvals)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def attach_hardware_sync_to_database(spec, comparisons: list[HardwareSyncComparison], database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    records = []
    for item in comparisons:
        artifacts = [
            artifact_from_path(path, name=name, artifact_type="hardware_sync_artifact")
            for name, path in artifact_paths.items()
        ]
        record = new_run_record(
            name=f"hardware_sync_{item.circuit_id}",
            run_type="qec_hardware_result_sync",
            status="completed" if item.passed_consistency_check else "needs_review",
            tags=["qec", "hardware_sync", item.backend_name],
            parameters={
                "job_id": item.job_id,
                "circuit_id": item.circuit_id,
                "backend_name": item.backend_name,
                "shots": item.shots,
            },
            metrics={
                "total_variation_distance": item.total_variation_distance,
                "passed_consistency_check": float(1 if item.passed_consistency_check else 0),
            },
            backend=BackendMetadataRecord(
                backend_name=item.backend_name,
                job_id=item.job_id,
                job_status=item.hardware_status,
                timestamp_unix=time.time(),
            ),
            artifacts=artifacts,
            notes="Hardware result synchronization scaffold. Counts may be imported or synthetic.",
        )
        db.append(record)
        records.append(record)
    return db, records


def make_hardware_sync_report(result: ProductionHardwareSyncResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.5 Hardware Result Synchronization Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Backend target",
        "",
        "```text",
        result.backend.summary(),
        "```",
        "",
        "## Job references",
        "",
    ]
    for item in result.job_references:
        lines.extend(["```text", item.summary(), "```", ""])
    lines.extend(["## Counts records", ""])
    for item in result.counts_records:
        lines.extend(["```text", item.summary(), "```", ""])
    lines.extend(["## Comparisons", ""])
    for item in result.comparisons:
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
        "## Safety note",
        "",
        "The default v4.5 sync path uses deterministic synthetic hardware-style counts. To use real IBM results, export job IDs/counts and pass them through the job/count import hooks.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_qec_hardware_sync_demo(output_dir, backend_name: str = "ibm_fez", rounds: int = 2, shots: int = 64):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hw = run_qec_hardware_demo(output_dir / "base_hardware_demo", backend_name=backend_name, rounds=rounds, shots=shots)
    refs = job_references_from_manifests(hw.job_manifests)
    counts, comparisons = sync_hardware_results(refs)

    backend = default_backend_target(backend_name)
    artifacts = {}
    artifacts["job_references_csv"] = str(export_job_references_csv(refs, output_dir / "job_references.csv"))
    artifacts["job_references_json"] = str(export_json_dataclasses(refs, output_dir / "job_references.json"))
    artifacts["counts_records_csv"] = str(export_counts_records_csv(counts, output_dir / "counts_records.csv"))
    artifacts["counts_records_json"] = str(export_json_dataclasses(counts, output_dir / "counts_records.json"))
    artifacts["sync_comparisons_csv"] = str(export_sync_comparisons_csv(comparisons, output_dir / "sync_comparisons.csv"))
    artifacts["sync_comparisons_json"] = str(export_json_dataclasses(comparisons, output_dir / "sync_comparisons.json"))
    artifacts["sync_comparison_figure"] = str(plot_sync_comparisons(comparisons, output_dir / "sync_comparisons.png"))

    result = ProductionHardwareSyncResult(
        project_name="qec_hardware_sync_demo",
        backend=backend,
        job_references=refs,
        counts_records=counts,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
        metadata={"base_hardware_artifacts": hw.artifacts},
    )
    artifacts["sync_report"] = str(make_hardware_sync_report(result, output_dir / "hardware_sync_report.md"))

    manifest_path = output_dir / "qec_hardware_sync_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.5 hardware sync demo",
        "summary": result.summary(),
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionHardwareSyncResult(
        project_name="qec_hardware_sync_demo",
        backend=backend,
        job_references=refs,
        counts_records=counts,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
        metadata={"base_hardware_artifacts": hw.artifacts},
    )


def run_production_qec_hardware_sync(
    spec_or_path,
    backend_name: str = "ibm_fez",
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    rounds: int = 3,
    job_ids_file: str | None = None,
    counts_file: str | None = None,
    physical_error_rate: float = 0.01,
    measurement_error_rate: float = 0.02,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir) / "qec_hardware_sync"
    output_dir.mkdir(parents=True, exist_ok=True)

    hw = run_production_qec_hardware_dry_run(
        spec,
        backend_name=backend_name,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        rounds=rounds,
        physical_error_rate=physical_error_rate,
        measurement_error_rate=measurement_error_rate,
    )

    if job_ids_file:
        refs = parse_job_ids_file(job_ids_file, backend_name=backend_name, default_shots=shots)
    else:
        refs = job_references_from_manifests(hw.job_manifests)

    imported_counts = parse_counts_file(counts_file) if counts_file else None
    counts, comparisons = sync_hardware_results(refs, imported_counts)

    backend = default_backend_target(backend_name)
    artifacts = {}
    artifacts["job_references_csv"] = str(export_job_references_csv(refs, output_dir / "job_references.csv"))
    artifacts["job_references_json"] = str(export_json_dataclasses(refs, output_dir / "job_references.json"))
    artifacts["counts_records_csv"] = str(export_counts_records_csv(counts, output_dir / "counts_records.csv"))
    artifacts["counts_records_json"] = str(export_json_dataclasses(counts, output_dir / "counts_records.json"))
    artifacts["sync_comparisons_csv"] = str(export_sync_comparisons_csv(comparisons, output_dir / "sync_comparisons.csv"))
    artifacts["sync_comparisons_json"] = str(export_json_dataclasses(comparisons, output_dir / "sync_comparisons.json"))
    artifacts["sync_comparison_figure"] = str(plot_sync_comparisons(comparisons, output_dir / "sync_comparisons.png"))

    db, records = attach_hardware_sync_to_database(
        spec=spec,
        comparisons=comparisons,
        database_path=Path(spec.output_dir) / "database" / "qec_hardware_sync.jsonl",
        artifact_paths={
            "job_references_csv": artifacts["job_references_csv"],
            "counts_records_csv": artifacts["counts_records_csv"],
            "sync_comparisons_csv": artifacts["sync_comparisons_csv"],
        },
    )
    artifacts["sync_database_jsonl"] = str(db.path)
    artifacts["sync_run_table_csv"] = str(export_run_table_csv(records, Path(spec.output_dir) / "database" / "qec_hardware_sync_run_table.csv"))
    artifacts["sync_dashboard_json"] = str(export_dashboard_json(records, Path(spec.output_dir) / "database" / "qec_hardware_sync_dashboard.json"))
    artifacts["sync_database_report"] = str(make_run_database_report(records, Path(spec.output_dir) / "database" / "qec_hardware_sync_database_report.md"))

    dashboard = build_dashboard_package(Path(spec.output_dir) / "dashboard_qec_hardware_sync", database_path=db.path)
    artifacts["sync_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["sync_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")

    warnings = list(hw.warnings)
    if job_ids_file is None:
        warnings.append("No job IDs file provided; used dry-run-derived synthetic sync job references.")
    if counts_file is None:
        warnings.append("No counts file provided; used deterministic synthetic hardware-style counts.")

    result = ProductionHardwareSyncResult(
        project_name=spec.project_name,
        backend=backend,
        job_references=refs,
        counts_records=counts,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"base_hardware_artifacts": hw.artifacts},
    )
    artifacts["sync_report"] = str(make_hardware_sync_report(result, output_dir / "hardware_sync_report.md"))

    manifest_path = output_dir / "production_qec_hardware_sync_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.5 production hardware result sync",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionHardwareSyncResult(
        project_name=spec.project_name,
        backend=backend,
        job_references=refs,
        counts_records=counts,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"base_hardware_artifacts": hw.artifacts},
    )
