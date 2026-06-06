from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import json
import time

from .experiment_db import (
    ExperimentDatabase,
    ExperimentRunRecord,
    BackendMetadataRecord,
    ArtifactRecord,
    artifact_from_path,
    new_run_record,
    create_demo_run_database,
    record_from_dict,
)
from .hardware_compare import (
    parse_counts_from_runtime_result,
    compare_counts,
    save_counts_comparison_csv,
    plot_counts_comparison,
    make_hardware_comparison_markdown_report,
    HardwareComparisonReportData,
)
from .dashboard import build_dashboard_package

try:
    from .ibm_results import retrieve_ibm_hardware_result, extract_sampler_counts
except Exception:
    retrieve_ibm_hardware_result = None
    extract_sampler_counts = None


TERMINAL_SUCCESS_STATUSES = {"DONE", "COMPLETED", "JobStatus.DONE"}
TERMINAL_FAILED_STATUSES = {"ERROR", "FAILED", "CANCELLED", "CANCELED", "JobStatus.ERROR", "JobStatus.CANCELLED"}
NONTERMINAL_STATUSES = {"QUEUED", "RUNNING", "INITIALIZING", "VALIDATING", "JobStatus.QUEUED", "JobStatus.RUNNING"}


@dataclass
class JobSyncResult:
    run_id: str | None
    job_id: str
    backend_name: str | None
    old_status: str | None
    new_status: str
    action: str
    counts: dict[str, int] | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal_success(self) -> bool:
        return self.new_status in TERMINAL_SUCCESS_STATUSES or self.new_status.upper() in {"DONE", "COMPLETED"}

    @property
    def is_terminal_failure(self) -> bool:
        return self.new_status in TERMINAL_FAILED_STATUSES or self.new_status.upper() in {"ERROR", "FAILED", "CANCELLED", "CANCELED"}

    def summary(self) -> str:
        return (
            "JobSyncResult\n"
            f"  run_id: {self.run_id}\n"
            f"  job_id: {self.job_id}\n"
            f"  backend_name: {self.backend_name}\n"
            f"  old_status: {self.old_status}\n"
            f"  new_status: {self.new_status}\n"
            f"  action: {self.action}\n"
            f"  counts: {self.counts}\n"
            f"  message: {self.message}"
        )


@dataclass
class DatabaseSyncSummary:
    database_path: str
    results: list[JobSyncResult]
    dashboard_artifacts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        actions = {}
        for result in self.results:
            actions[result.action] = actions.get(result.action, 0) + 1
        return (
            "DatabaseSyncSummary\n"
            f"  database_path: {self.database_path}\n"
            f"  results: {len(self.results)}\n"
            f"  actions: {actions}\n"
            f"  dashboard_artifacts: {len(self.dashboard_artifacts)}"
        )


def normalize_job_status(status) -> str:
    text = str(status)
    if "." in text:
        text = text.split(".")[-1]
    return text.upper()


def is_success_status(status) -> bool:
    return normalize_job_status(status) in {"DONE", "COMPLETED"}


def is_failure_status(status) -> bool:
    return normalize_job_status(status) in {"ERROR", "FAILED", "CANCELLED", "CANCELED"}


def is_pending_status(status) -> bool:
    return normalize_job_status(status) in {"QUEUED", "RUNNING", "INITIALIZING", "VALIDATING"}


def get_job_ids_from_records(records: list[ExperimentRunRecord]) -> list[str]:
    job_ids = []
    for record in records:
        if record.backend and record.backend.job_id:
            job_ids.append(record.backend.job_id)
    return job_ids


def update_record_status(record: ExperimentRunRecord, new_status: str, counts_artifact: ArtifactRecord | None = None):
    if record.backend:
        record.backend.job_status = new_status
        record.backend.timestamp_unix = time.time()
    record.status = "completed" if is_success_status(new_status) else ("failed" if is_failure_status(new_status) else "pending")
    if counts_artifact is not None:
        record.artifacts.append(counts_artifact)
    record.metadata["last_sync_unix"] = time.time()
    return record


def _rewrite_database(path, records: list[ExperimentRunRecord]):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")
    return path


def mock_job_payload(job_id: str, status: str = "DONE", backend_name: str = "mock_ibm_backend", counts=None):
    return {
        "job_id": job_id,
        "status": status,
        "backend_name": backend_name,
        "result": {
            "counts": counts or {"00": 470, "01": 30, "10": 34, "11": 490}
        },
    }


def sync_job_from_payload(
    payload: dict[str, Any],
    output_dir,
    simulator_counts: dict[str, int] | None = None,
    run_id: str | None = None,
    old_status: str | None = None,
) -> JobSyncResult:
    """Synchronize one job using a payload, useful for saved/mock IBM results."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    job_id = str(payload.get("job_id", "unknown_job"))
    backend_name = payload.get("backend_name")
    new_status = normalize_job_status(payload.get("status", "UNKNOWN"))
    result_payload = payload.get("result")
    counts = parse_counts_from_runtime_result(result_payload)

    artifacts = {}
    action = "status_refreshed"
    message = "Status refreshed."

    if is_success_status(new_status) and counts:
        counts_path = output_dir / f"{job_id}_hardware_counts.json"
        counts_path.write_text(json.dumps(counts, indent=2), encoding="utf-8")
        artifacts["hardware_counts_json"] = str(counts_path)
        action = "retrieved_counts"
        message = "Job completed and counts were retrieved."

        if simulator_counts is not None:
            comparison = compare_counts(simulator_counts, counts)
            csv_path = save_counts_comparison_csv(comparison, output_dir / f"{job_id}_counts_comparison.csv")
            fig_path = plot_counts_comparison(comparison, output_dir / f"{job_id}_counts_comparison.png")
            report_data = HardwareComparisonReportData(
                counts_comparison=comparison,
                job_metadata={"job_id": job_id, "backend_name": backend_name, "status": new_status},
                artifacts={
                    "hardware_counts_json": str(counts_path),
                    "counts_comparison_csv": str(csv_path),
                    "counts_comparison_figure": str(fig_path),
                },
            )
            report_path = make_hardware_comparison_markdown_report(
                report_data,
                output_dir / f"{job_id}_hardware_comparison_report.md",
            )
            artifacts["counts_comparison_csv"] = str(csv_path)
            artifacts["counts_comparison_figure"] = str(fig_path)
            artifacts["hardware_comparison_report"] = str(report_path)
    elif is_failure_status(new_status):
        action = "terminal_failure_detected"
        message = "Job is in a terminal failure/cancelled state."
    elif is_pending_status(new_status):
        action = "still_pending"
        message = "Job is not terminal yet."
    else:
        action = "unknown_status"
        message = "Job status was not recognized."

    return JobSyncResult(
        run_id=run_id,
        job_id=job_id,
        backend_name=backend_name,
        old_status=old_status,
        new_status=new_status,
        action=action,
        counts=counts,
        artifacts=artifacts,
        message=message,
        metadata={"source": "payload"},
    )


def sync_ibm_job(
    job_id: str,
    output_dir,
    backend_name: str | None = None,
    simulator_counts: dict[str, int] | None = None,
    run_id: str | None = None,
    old_status: str | None = None,
) -> JobSyncResult:
    """Synchronize one real IBM job by retrieving its current result.

    This does not submit a job. It only retrieves an existing job.
    """
    if retrieve_ibm_hardware_result is None:
        raise ImportError("Flexible IBM result retrieval helper is not available.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hardware = retrieve_ibm_hardware_result(job_id=job_id, backend_name=backend_name)
    payload = {
        "job_id": hardware.job_id,
        "backend_name": hardware.backend_name,
        "status": hardware.status,
        "result": {"counts": hardware.counts or {}},
    }
    return sync_job_from_payload(
        payload,
        output_dir=output_dir,
        simulator_counts=simulator_counts,
        run_id=run_id,
        old_status=old_status,
    )


def sync_database_with_payloads(
    database_path,
    payloads: list[dict[str, Any]],
    output_dir,
    simulator_counts: dict[str, int] | None = None,
    rebuild_dashboard: bool = True,
) -> DatabaseSyncSummary:
    """Update an ExperimentDatabase using provided job payloads."""
    database_path = Path(database_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = ExperimentDatabase(database_path)
    records = db.read_all()
    payload_by_job = {str(p.get("job_id")): p for p in payloads}

    results = []
    updated_records = []

    for record in records:
        old_status = record.backend.job_status if record.backend else None
        job_id = record.backend.job_id if record.backend else None

        if job_id and job_id in payload_by_job:
            result = sync_job_from_payload(
                payload_by_job[job_id],
                output_dir=output_dir / "synced_jobs",
                simulator_counts=simulator_counts,
                run_id=record.run_id,
                old_status=old_status,
            )
            results.append(result)

            counts_artifact = None
            if "hardware_counts_json" in result.artifacts:
                counts_artifact = artifact_from_path(
                    result.artifacts["hardware_counts_json"],
                    name=f"{job_id}_hardware_counts",
                    artifact_type="hardware_counts_json",
                )
            update_record_status(record, result.new_status, counts_artifact=counts_artifact)
            record.metrics["last_sync_has_counts"] = 1.0 if result.counts else 0.0
            if result.action == "terminal_failure_detected":
                record.metrics["sync_failure_detected"] = 1.0
        updated_records.append(record)

    _rewrite_database(database_path, updated_records)

    dashboard_artifacts = {}
    if rebuild_dashboard:
        try:
            package = build_dashboard_package(output_dir / "dashboard", database_path=database_path)
            dashboard_artifacts = package.artifacts
        except Exception as exc:
            dashboard_artifacts = {"dashboard_error": str(exc)}

    return DatabaseSyncSummary(
        database_path=str(database_path),
        results=results,
        dashboard_artifacts=dashboard_artifacts,
        metadata={"payload_count": len(payloads), "records_count": len(records)},
    )


def export_sync_results_csv(results: list[JobSyncResult], path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "run_id", "job_id", "backend_name", "old_status", "new_status",
            "action", "has_counts", "message", "artifacts_json"
        ])
        for r in results:
            writer.writerow([
                r.run_id,
                r.job_id,
                r.backend_name,
                r.old_status,
                r.new_status,
                r.action,
                r.counts is not None,
                r.message,
                json.dumps(r.artifacts, default=str),
            ])
    return path


def make_sync_markdown_report(summary: DatabaseSyncSummary, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v2.9 Job Synchronization Report",
        "",
        "## Summary",
        "",
        "```text",
        summary.summary(),
        "```",
        "",
        "## Job results",
        "",
    ]
    if not summary.results:
        lines.append("No matching jobs were synchronized.")
    for result in summary.results:
        lines.extend(["```text", result.summary(), "```", ""])
        if result.artifacts:
            lines.append("Artifacts:")
            for key, value in result.artifacts.items():
                lines.append(f"- **{key}**: `{value}`")
            lines.append("")

    lines.extend([
        "## Dashboard artifacts",
        "",
    ])
    for key, value in summary.dashboard_artifacts.items():
        lines.append(f"- **{key}**: `{value}`")

    lines.extend([
        "",
        "## Safety note",
        "",
        "This synchronization layer retrieves or processes existing job records. It does not submit new hardware jobs.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_mock_sync_workflow(output_dir):
    """Create a demo database, then synchronize one mock hardware job."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create demo database with a mock hardware job id.
    db, records, db_artifacts = create_demo_run_database(output_dir / "database")
    database_path = db.path

    payloads = [
        mock_job_payload(
            job_id="mock_job_id",
            status="DONE",
            backend_name="mock_ibm_backend",
            counts={"00": 470, "01": 30, "10": 34, "11": 490},
        )
    ]

    simulator_counts = {"00": 510, "11": 514}
    summary = sync_database_with_payloads(
        database_path=database_path,
        payloads=payloads,
        output_dir=output_dir / "sync",
        simulator_counts=simulator_counts,
        rebuild_dashboard=True,
    )

    artifacts = {}
    artifacts["sync_results_csv"] = str(export_sync_results_csv(summary.results, output_dir / "sync_results.csv"))
    artifacts["sync_markdown_report"] = str(make_sync_markdown_report(summary, output_dir / "sync_report.md"))

    manifest = {
        "package": "AZM-QOS v2.9 job synchronization",
        "database_path": str(database_path),
        "sync_results": [asdict(r) for r in summary.results],
        "dashboard_artifacts": summary.dashboard_artifacts,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "sync_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    summary.dashboard_artifacts.update(artifacts)
    return summary


def run_mock_failure_sync_workflow(output_dir):
    """Demo detection of failed/cancelled jobs."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = ExperimentDatabase(output_dir / "failure_runs.jsonl")
    record = new_run_record(
        name="mock_failed_job_run",
        run_type="hardware",
        status="pending",
        tags=["hardware", "sync", "failure-demo"],
        backend=BackendMetadataRecord(
            backend_name="mock_ibm_backend",
            job_id="mock_failed_job",
            job_status="RUNNING",
            timestamp_unix=time.time(),
        ),
        parameters={"shots": 1024},
    )
    db.append(record)

    payloads = [mock_job_payload(job_id="mock_failed_job", status="CANCELLED", backend_name="mock_ibm_backend", counts={})]
    summary = sync_database_with_payloads(
        database_path=db.path,
        payloads=payloads,
        output_dir=output_dir / "failure_sync",
        simulator_counts=None,
        rebuild_dashboard=True,
    )
    return summary
