from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import time

from .production import load_production_spec
from .qec_hardware_sync import (
    HardwareJobReference,
    HardwareCountsRecord,
    HardwareSyncComparison,
    ProductionHardwareSyncResult,
    parse_job_ids_file,
    synthetic_hardware_counts_for_job,
    sync_hardware_results,
    export_job_references_csv,
    export_counts_records_csv,
    export_sync_comparisons_csv,
    export_json_dataclasses,
    plot_sync_comparisons,
    make_hardware_sync_report,
)
from .qec_hardware import default_backend_target, BackendTargetSpec
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
class RuntimeFetchConfig:
    backend_name: str = "ibm_fez"
    channel: str | None = None
    instance: str | None = None
    token_env_var: str = "QISKIT_IBM_TOKEN"
    enable_runtime_fetch: bool = False
    use_cache: bool = True
    force_refresh: bool = False
    max_retries: int = 3
    retry_sleep_seconds: float = 0.25
    synthetic_fallback: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "RuntimeFetchConfig\n"
            f"  backend_name: {self.backend_name}\n"
            f"  channel: {self.channel}\n"
            f"  instance: {self.instance}\n"
            f"  token_env_var: {self.token_env_var}\n"
            f"  enable_runtime_fetch: {self.enable_runtime_fetch}\n"
            f"  use_cache: {self.use_cache}\n"
            f"  force_refresh: {self.force_refresh}\n"
            f"  max_retries: {self.max_retries}\n"
            f"  retry_sleep_seconds: {self.retry_sleep_seconds}\n"
            f"  synthetic_fallback: {self.synthetic_fallback}"
        )


@dataclass
class RuntimeJobStatusRecord:
    job_id: str
    backend_name: str
    status: str
    source: str
    cached: bool = False
    fetched_at_unix: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "RuntimeJobStatusRecord\n"
            f"  job_id: {self.job_id}\n"
            f"  backend: {self.backend_name}\n"
            f"  status: {self.status}\n"
            f"  source: {self.source}\n"
            f"  cached: {self.cached}"
        )


@dataclass
class RuntimeFetchRecord:
    job_reference: HardwareJobReference
    status_record: RuntimeJobStatusRecord
    counts_record: HardwareCountsRecord
    source: str
    cached: bool = False
    cache_path: str | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "RuntimeFetchRecord\n"
            f"  job_id: {self.job_reference.job_id}\n"
            f"  circuit: {self.job_reference.circuit_id}\n"
            f"  source: {self.source}\n"
            f"  cached: {self.cached}\n"
            f"  status: {self.status_record.status}\n"
            f"  outcomes: {len(self.counts_record.counts)}\n"
            f"  warnings: {self.warnings}"
        )


@dataclass
class RuntimeSyncResult:
    project_name: str
    backend: BackendTargetSpec
    config: RuntimeFetchConfig
    fetch_records: list[RuntimeFetchRecord]
    comparisons: list[HardwareSyncComparison]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        real = sum(1 for x in self.fetch_records if x.source == "runtime")
        synthetic = sum(1 for x in self.fetch_records if "synthetic" in x.source)
        cached = sum(1 for x in self.fetch_records if x.cached)
        passed = sum(1 for x in self.comparisons if x.passed_consistency_check)
        return (
            "RuntimeSyncResult\n"
            f"  project: {self.project_name}\n"
            f"  backend: {self.backend.backend_name}\n"
            f"  fetch_records: {len(self.fetch_records)}\n"
            f"  runtime_records: {real}\n"
            f"  synthetic_records: {synthetic}\n"
            f"  cached_records: {cached}\n"
            f"  comparisons: {len(self.comparisons)}\n"
            f"  consistency_passed: {passed}/{len(self.comparisons)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def runtime_package_available() -> bool:
    try:
        import qiskit_ibm_runtime  # noqa: F401
        return True
    except Exception:
        return False


def make_runtime_service(config: RuntimeFetchConfig):
    if not config.enable_runtime_fetch:
        raise RuntimeError("Runtime fetch is disabled. Pass enable_runtime_fetch=True to construct the service.")
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except Exception as exc:
        raise ImportError("qiskit-ibm-runtime is not installed. Install with: python -m pip install qiskit-ibm-runtime") from exc

    kwargs = {}
    if config.channel:
        kwargs["channel"] = config.channel
    if config.instance:
        kwargs["instance"] = config.instance
    return QiskitRuntimeService(**kwargs)


def cache_key_for_job(job: HardwareJobReference) -> str:
    digest = hashlib.sha256(f"{job.job_id}|{job.backend_name}|{job.circuit_id}|{job.shots}".encode("utf-8")).hexdigest()[:24]
    return digest


def cache_path_for_job(cache_dir, job: HardwareJobReference):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{cache_key_for_job(job)}.json"


def load_cached_fetch_record(cache_dir, job: HardwareJobReference) -> RuntimeFetchRecord | None:
    path = cache_path_for_job(cache_dir, job)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    job_ref = HardwareJobReference(**data["job_reference"])
    status = RuntimeJobStatusRecord(**data["status_record"])
    counts = HardwareCountsRecord(**data["counts_record"])
    return RuntimeFetchRecord(
        job_reference=job_ref,
        status_record=status,
        counts_record=counts,
        source=data.get("source", "cache"),
        cached=True,
        cache_path=str(path),
        warnings=list(data.get("warnings", [])),
        metadata=dict(data.get("metadata", {})),
    )


def save_fetch_record_to_cache(cache_dir, record: RuntimeFetchRecord):
    path = cache_path_for_job(cache_dir, record.job_reference)
    payload = asdict(record)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
    return path


def _extract_counts_from_runtime_result(result_obj) -> dict[str, int]:
    """Best-effort parser for multiple Qiskit result shapes."""
    if result_obj is None:
        return {}

    if isinstance(result_obj, dict):
        if "counts" in result_obj and isinstance(result_obj["counts"], dict):
            return {str(k): int(v) for k, v in result_obj["counts"].items()}
        if "quasi_dists" in result_obj:
            # Convert quasi distribution to pseudo-counts using 1024 if no shots known.
            qd = result_obj["quasi_dists"][0] if isinstance(result_obj["quasi_dists"], list) else result_obj["quasi_dists"]
            return {str(k): int(round(float(v) * 1024)) for k, v in dict(qd).items()}

    if hasattr(result_obj, "get_counts"):
        counts = result_obj.get_counts()
        if isinstance(counts, list):
            counts = counts[0]
        return {str(k): int(v) for k, v in dict(counts).items()}

    if hasattr(result_obj, "data"):
        try:
            data = result_obj.data()
            if isinstance(data, dict) and "counts" in data:
                return {str(k): int(v) for k, v in data["counts"].items()}
        except Exception:
            pass

    return {}


def fetch_runtime_job_status(job: HardwareJobReference, config: RuntimeFetchConfig, service=None) -> RuntimeJobStatusRecord:
    if not config.enable_runtime_fetch:
        return RuntimeJobStatusRecord(
            job_id=job.job_id,
            backend_name=job.backend_name,
            status="SYNTHETIC_STATUS",
            source="synthetic",
            cached=False,
            metadata={"reason": "runtime_fetch_disabled"},
        )

    service = service or make_runtime_service(config)
    runtime_job = service.job(job.job_id)
    status = str(runtime_job.status())
    return RuntimeJobStatusRecord(
        job_id=job.job_id,
        backend_name=job.backend_name,
        status=status,
        source="runtime",
        cached=False,
    )


def fetch_runtime_counts(job: HardwareJobReference, config: RuntimeFetchConfig, service=None) -> HardwareCountsRecord:
    if not config.enable_runtime_fetch:
        return synthetic_hardware_counts_for_job(job)

    service = service or make_runtime_service(config)
    runtime_job = service.job(job.job_id)
    result_obj = runtime_job.result()
    counts = _extract_counts_from_runtime_result(result_obj)
    if not counts:
        if config.synthetic_fallback:
            synthetic = synthetic_hardware_counts_for_job(job)
            synthetic.status = "SYNTHETIC_FALLBACK_EMPTY_RUNTIME_COUNTS"
            return synthetic
        raise RuntimeError(f"Could not extract counts from runtime result for job {job.job_id}")

    shots = sum(counts.values()) or job.shots
    return HardwareCountsRecord(
        job_id=job.job_id,
        backend_name=job.backend_name,
        circuit_id=job.circuit_id,
        counts=counts,
        shots=shots,
        status="RUNTIME_SYNCED",
        metadata={"runtime_fetch": True},
    )


def fetch_job_with_retry(job: HardwareJobReference, config: RuntimeFetchConfig, cache_dir=None, service=None) -> RuntimeFetchRecord:
    cache_dir = Path(cache_dir) if cache_dir else None
    if cache_dir and config.use_cache and not config.force_refresh:
        cached = load_cached_fetch_record(cache_dir, job)
        if cached is not None:
            cached.status_record.cached = True
            cached.cached = True
            return cached

    warnings = []
    last_error = None
    service_obj = service

    for attempt in range(max(1, config.max_retries)):
        try:
            if config.enable_runtime_fetch:
                if service_obj is None:
                    service_obj = make_runtime_service(config)
                status = fetch_runtime_job_status(job, config, service=service_obj)
                counts = fetch_runtime_counts(job, config, service=service_obj)
                record = RuntimeFetchRecord(
                    job_reference=job,
                    status_record=status,
                    counts_record=counts,
                    source="runtime",
                    cached=False,
                    warnings=warnings,
                    metadata={"attempt": attempt + 1},
                )
            else:
                status = fetch_runtime_job_status(job, config)
                counts = synthetic_hardware_counts_for_job(job)
                record = RuntimeFetchRecord(
                    job_reference=job,
                    status_record=status,
                    counts_record=counts,
                    source="synthetic_runtime_disabled",
                    cached=False,
                    warnings=["Runtime fetch disabled; used synthetic hardware-style counts."],
                    metadata={"attempt": attempt + 1},
                )

            if cache_dir and config.use_cache:
                record.cache_path = str(save_fetch_record_to_cache(cache_dir, record))
            return record

        except Exception as exc:
            last_error = exc
            warnings.append(f"attempt {attempt + 1} failed: {exc}")
            if attempt + 1 < config.max_retries:
                time.sleep(max(0.0, config.retry_sleep_seconds))

    if config.synthetic_fallback:
        status = RuntimeJobStatusRecord(
            job_id=job.job_id,
            backend_name=job.backend_name,
            status="SYNTHETIC_FALLBACK_AFTER_FETCH_FAILURE",
            source="synthetic",
            metadata={"last_error": str(last_error)},
        )
        counts = synthetic_hardware_counts_for_job(job)
        record = RuntimeFetchRecord(
            job_reference=job,
            status_record=status,
            counts_record=counts,
            source="synthetic_fallback",
            cached=False,
            warnings=warnings + [f"Used synthetic fallback after fetch failure: {last_error}"],
        )
        if cache_dir and config.use_cache:
            record.cache_path = str(save_fetch_record_to_cache(cache_dir, record))
        return record

    raise RuntimeError(f"Runtime fetch failed for job {job.job_id}: {last_error}")


def fetch_jobs_with_runtime_adapter(jobs: list[HardwareJobReference], config: RuntimeFetchConfig, cache_dir=None) -> list[RuntimeFetchRecord]:
    service = None
    if config.enable_runtime_fetch:
        try:
            service = make_runtime_service(config)
        except Exception:
            service = None
            if not config.synthetic_fallback:
                raise

    return [fetch_job_with_retry(job, config, cache_dir=cache_dir, service=service) for job in jobs]


def export_runtime_fetch_records_csv(items: list[RuntimeFetchRecord], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["job_id", "backend_name", "circuit_id", "source", "cached", "status", "shots", "outcomes", "warnings"])
        for x in items:
            writer.writerow([
                x.job_reference.job_id,
                x.job_reference.backend_name,
                x.job_reference.circuit_id,
                x.source,
                x.cached,
                x.status_record.status,
                x.counts_record.shots,
                len(x.counts_record.counts),
                json.dumps(x.warnings),
            ])
    return path


def export_runtime_fetch_records_json(items: list[RuntimeFetchRecord], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(x) for x in items], indent=2, default=_json_default), encoding="utf-8")
    return path


def attach_runtime_sync_to_database(spec, result: RuntimeSyncResult, database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    records = []

    comparisons_by_job = {x.job_id: x for x in result.comparisons}
    for fetch in result.fetch_records:
        comp = comparisons_by_job.get(fetch.job_reference.job_id)
        artifacts = [
            artifact_from_path(path, name=name, artifact_type="runtime_sync_artifact")
            for name, path in artifact_paths.items()
        ]
        record = new_run_record(
            name=f"runtime_sync_{fetch.job_reference.circuit_id}",
            run_type="qec_runtime_fetch_sync",
            status="completed" if comp and comp.passed_consistency_check else "needs_review",
            tags=["qec", "runtime_fetch", fetch.source, fetch.job_reference.backend_name],
            parameters={
                "job_id": fetch.job_reference.job_id,
                "circuit_id": fetch.job_reference.circuit_id,
                "backend_name": fetch.job_reference.backend_name,
                "source": fetch.source,
                "cached": fetch.cached,
            },
            metrics={
                "counts_outcomes": float(len(fetch.counts_record.counts)),
                "shots": float(fetch.counts_record.shots),
                "total_variation_distance": float(comp.total_variation_distance if comp else 0.0),
                "passed_consistency_check": float(1 if comp and comp.passed_consistency_check else 0),
            },
            backend=BackendMetadataRecord(
                backend_name=fetch.job_reference.backend_name,
                job_id=fetch.job_reference.job_id,
                job_status=fetch.status_record.status,
                timestamp_unix=time.time(),
            ),
            artifacts=artifacts,
            notes="Runtime fetch/sync record. Source indicates runtime or synthetic fallback.",
        )
        db.append(record)
        records.append(record)
    return db, records


def make_runtime_sync_report(result: RuntimeSyncResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.6 IBM Runtime Fetch and Hardware Sync Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Runtime fetch config",
        "",
        "```text",
        result.config.summary(),
        "```",
        "",
        "## Fetch records",
        "",
    ]
    for item in result.fetch_records:
        lines.extend(["```text", item.summary(), "```", ""])
    lines.extend(["## Sync comparisons", ""])
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
        "Runtime fetch is optional and disabled by default. Synthetic records are clearly labeled. No hardware jobs are submitted by this workflow.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_runtime_fetch_demo(output_dir, backend_name: str = "ibm_fez", rounds: int = 2, shots: int = 64):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    from .qec_hardware_sync import run_qec_hardware_sync_demo
    base = run_qec_hardware_sync_demo(output_dir / "base_sync_demo", backend_name=backend_name, rounds=rounds, shots=shots)
    jobs = base.job_references
    config = RuntimeFetchConfig(backend_name=backend_name, enable_runtime_fetch=False, use_cache=True)
    cache_dir = output_dir / "runtime_cache"
    fetch_records = fetch_jobs_with_runtime_adapter(jobs, config, cache_dir=cache_dir)

    counts_records = [x.counts_record for x in fetch_records]
    _, comparisons = sync_hardware_results(jobs, counts_records)

    backend = default_backend_target(backend_name)
    artifacts = {}
    artifacts["runtime_fetch_records_csv"] = str(export_runtime_fetch_records_csv(fetch_records, output_dir / "runtime_fetch_records.csv"))
    artifacts["runtime_fetch_records_json"] = str(export_runtime_fetch_records_json(fetch_records, output_dir / "runtime_fetch_records.json"))
    artifacts["job_references_csv"] = str(export_job_references_csv(jobs, output_dir / "job_references.csv"))
    artifacts["counts_records_csv"] = str(export_counts_records_csv(counts_records, output_dir / "counts_records.csv"))
    artifacts["sync_comparisons_csv"] = str(export_sync_comparisons_csv(comparisons, output_dir / "sync_comparisons.csv"))
    artifacts["sync_comparisons_json"] = str(export_json_dataclasses(comparisons, output_dir / "sync_comparisons.json"))
    artifacts["sync_comparison_figure"] = str(plot_sync_comparisons(comparisons, output_dir / "sync_comparisons.png"))

    warnings = []
    if not runtime_package_available():
        warnings.append("qiskit-ibm-runtime is not installed; Runtime fetch capability unavailable.")
    warnings.append("Runtime fetch disabled in demo; synthetic hardware-style counts were used.")

    result = RuntimeSyncResult(
        project_name="runtime_fetch_demo",
        backend=backend,
        config=config,
        fetch_records=fetch_records,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"base_sync_artifacts": base.artifacts, "runtime_package_available": runtime_package_available()},
    )
    artifacts["runtime_sync_report"] = str(make_runtime_sync_report(result, output_dir / "runtime_sync_report.md"))

    manifest_path = output_dir / "runtime_fetch_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.6 Runtime fetch demo",
        "summary": result.summary(),
        "warnings": warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return RuntimeSyncResult(
        project_name="runtime_fetch_demo",
        backend=backend,
        config=config,
        fetch_records=fetch_records,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"base_sync_artifacts": base.artifacts, "runtime_package_available": runtime_package_available()},
    )


def run_production_runtime_sync(
    spec_or_path,
    backend_name: str = "ibm_fez",
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    rounds: int = 3,
    job_ids_file: str | None = None,
    enable_runtime_fetch: bool = False,
    force_refresh: bool = False,
    physical_error_rate: float = 0.01,
    measurement_error_rate: float = 0.02,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir) / "runtime_sync"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build the v4.5 sync baseline to get dry-run-derived job refs unless user supplied job IDs.
    from .qec_hardware_sync import run_production_qec_hardware_sync
    base = run_production_qec_hardware_sync(
        spec,
        backend_name=backend_name,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        rounds=rounds,
        job_ids_file=job_ids_file,
        counts_file=None,
        physical_error_rate=physical_error_rate,
        measurement_error_rate=measurement_error_rate,
    )

    if job_ids_file:
        jobs = parse_job_ids_file(job_ids_file, backend_name=backend_name, default_shots=shots)
    else:
        jobs = base.job_references

    config = RuntimeFetchConfig(
        backend_name=backend_name,
        enable_runtime_fetch=enable_runtime_fetch,
        force_refresh=force_refresh,
        use_cache=True,
        synthetic_fallback=True,
    )
    cache_dir = output_dir / "runtime_cache"
    fetch_records = fetch_jobs_with_runtime_adapter(jobs, config, cache_dir=cache_dir)
    counts_records = [x.counts_record for x in fetch_records]
    _, comparisons = sync_hardware_results(jobs, counts_records)

    backend = default_backend_target(backend_name)
    artifacts = {}
    artifacts["runtime_fetch_records_csv"] = str(export_runtime_fetch_records_csv(fetch_records, output_dir / "runtime_fetch_records.csv"))
    artifacts["runtime_fetch_records_json"] = str(export_runtime_fetch_records_json(fetch_records, output_dir / "runtime_fetch_records.json"))
    artifacts["job_references_csv"] = str(export_job_references_csv(jobs, output_dir / "job_references.csv"))
    artifacts["job_references_json"] = str(export_json_dataclasses(jobs, output_dir / "job_references.json"))
    artifacts["counts_records_csv"] = str(export_counts_records_csv(counts_records, output_dir / "counts_records.csv"))
    artifacts["counts_records_json"] = str(export_json_dataclasses(counts_records, output_dir / "counts_records.json"))
    artifacts["sync_comparisons_csv"] = str(export_sync_comparisons_csv(comparisons, output_dir / "sync_comparisons.csv"))
    artifacts["sync_comparisons_json"] = str(export_json_dataclasses(comparisons, output_dir / "sync_comparisons.json"))
    artifacts["sync_comparison_figure"] = str(plot_sync_comparisons(comparisons, output_dir / "sync_comparisons.png"))

    warnings = list(base.warnings)
    if not runtime_package_available():
        warnings.append("qiskit-ibm-runtime is not installed; real Runtime fetch unavailable.")
    if not enable_runtime_fetch:
        warnings.append("Runtime fetch disabled; used synthetic hardware-style counts.")
    if not job_ids_file:
        warnings.append("No job IDs file provided; used dry-run-derived job references.")

    result = RuntimeSyncResult(
        project_name=spec.project_name,
        backend=backend,
        config=config,
        fetch_records=fetch_records,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"base_sync_artifacts": base.artifacts, "runtime_package_available": runtime_package_available()},
    )

    db, records = attach_runtime_sync_to_database(
        spec=spec,
        result=result,
        database_path=Path(spec.output_dir) / "database" / "runtime_sync.jsonl",
        artifact_paths={
            "runtime_fetch_records_csv": artifacts["runtime_fetch_records_csv"],
            "counts_records_csv": artifacts["counts_records_csv"],
            "sync_comparisons_csv": artifacts["sync_comparisons_csv"],
        },
    )
    artifacts["runtime_database_jsonl"] = str(db.path)
    artifacts["runtime_run_table_csv"] = str(export_run_table_csv(records, Path(spec.output_dir) / "database" / "runtime_sync_run_table.csv"))
    artifacts["runtime_dashboard_json"] = str(export_dashboard_json(records, Path(spec.output_dir) / "database" / "runtime_sync_dashboard.json"))
    artifacts["runtime_database_report"] = str(make_run_database_report(records, Path(spec.output_dir) / "database" / "runtime_sync_database_report.md"))

    dashboard = build_dashboard_package(Path(spec.output_dir) / "dashboard_runtime_sync", database_path=db.path)
    artifacts["runtime_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["runtime_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")

    result.artifacts = artifacts
    artifacts["runtime_sync_report"] = str(make_runtime_sync_report(result, output_dir / "runtime_sync_report.md"))

    manifest_path = output_dir / "production_runtime_sync_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.6 production Runtime sync",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return RuntimeSyncResult(
        project_name=spec.project_name,
        backend=backend,
        config=config,
        fetch_records=fetch_records,
        comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"base_sync_artifacts": base.artifacts, "runtime_package_available": runtime_package_available()},
    )
