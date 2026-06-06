from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import json
import time
import uuid


@dataclass
class ArtifactRecord:
    name: str
    path: str
    artifact_type: str = "file"
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return f"ArtifactRecord(name={self.name}, type={self.artifact_type}, path={self.path})"


@dataclass
class BackendMetadataRecord:
    backend_name: str | None = None
    num_qubits: int | None = None
    basis_gates: list[str] = field(default_factory=list)
    job_id: str | None = None
    job_status: str | None = None
    timestamp_unix: float | None = None
    calibration_timestamp: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"BackendMetadataRecord(backend={self.backend_name}, job_id={self.job_id}, "
            f"status={self.job_status}, qubits={self.num_qubits})"
        )


@dataclass
class ExperimentRunRecord:
    run_id: str
    name: str
    created_at_unix: float
    azmqos_version: str = "2.7.0"
    run_type: str = "generic"
    status: str = "created"
    tags: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    backend: BackendMetadataRecord | None = None
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ExperimentRunRecord\n"
            f"  run_id: {self.run_id}\n"
            f"  name: {self.name}\n"
            f"  run_type: {self.run_type}\n"
            f"  status: {self.status}\n"
            f"  tags: {self.tags}\n"
            f"  metrics: {self.metrics}\n"
            f"  artifacts: {len(self.artifacts)}"
        )

    def to_dict(self):
        return asdict(self)


def new_run_record(
    name: str,
    run_type: str = "generic",
    status: str = "created",
    tags: list[str] | None = None,
    parameters: dict[str, Any] | None = None,
    metrics: dict[str, float] | None = None,
    backend: BackendMetadataRecord | None = None,
    artifacts: list[ArtifactRecord] | None = None,
    notes: str | None = None,
    **metadata,
) -> ExperimentRunRecord:
    return ExperimentRunRecord(
        run_id=str(uuid.uuid4()),
        name=name,
        created_at_unix=time.time(),
        run_type=run_type,
        status=status,
        tags=tags or [],
        parameters=parameters or {},
        metrics=metrics or {},
        backend=backend,
        artifacts=artifacts or [],
        notes=notes,
        metadata=metadata,
    )


def artifact_from_path(path, name: str | None = None, artifact_type: str = "file", description: str | None = None):
    path = Path(path)
    return ArtifactRecord(
        name=name or path.name,
        path=str(path),
        artifact_type=artifact_type,
        description=description,
        metadata={"exists": path.exists(), "suffix": path.suffix},
    )


def backend_record_from_hardware_result(hardware_result) -> BackendMetadataRecord:
    return BackendMetadataRecord(
        backend_name=getattr(hardware_result, "backend_name", None),
        job_id=getattr(hardware_result, "job_id", None),
        job_status=getattr(hardware_result, "status", None),
        timestamp_unix=time.time(),
        metadata={"source": "hardware_result"},
    )


class ExperimentDatabase:
    """Simple JSONL database for AZM-QOS run tracking."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: ExperimentRunRecord):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")
        return record.run_id

    def read_all(self) -> list[ExperimentRunRecord]:
        records = []
        if not self.path.exists():
            return records

        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            records.append(record_from_dict(data))
        return records

    def get(self, run_id: str) -> ExperimentRunRecord | None:
        for record in self.read_all():
            if record.run_id == run_id:
                return record
        return None

    def query(
        self,
        run_type: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        backend_name: str | None = None,
        metric_min: dict[str, float] | None = None,
        metric_max: dict[str, float] | None = None,
    ) -> list[ExperimentRunRecord]:
        out = []
        for record in self.read_all():
            if run_type is not None and record.run_type != run_type:
                continue
            if status is not None and record.status != status:
                continue
            if tag is not None and tag not in record.tags:
                continue
            if backend_name is not None:
                if record.backend is None or record.backend.backend_name != backend_name:
                    continue
            if metric_min:
                if any(record.metrics.get(k, float("-inf")) < v for k, v in metric_min.items()):
                    continue
            if metric_max:
                if any(record.metrics.get(k, float("inf")) > v for k, v in metric_max.items()):
                    continue
            out.append(record)
        return out

    def summary(self) -> str:
        records = self.read_all()
        by_type = {}
        by_status = {}
        for r in records:
            by_type[r.run_type] = by_type.get(r.run_type, 0) + 1
            by_status[r.status] = by_status.get(r.status, 0) + 1
        return (
            "ExperimentDatabase\n"
            f"  path: {self.path}\n"
            f"  runs: {len(records)}\n"
            f"  by_type: {by_type}\n"
            f"  by_status: {by_status}"
        )


def record_from_dict(data: dict[str, Any]) -> ExperimentRunRecord:
    backend_data = data.get("backend")
    backend = BackendMetadataRecord(**backend_data) if isinstance(backend_data, dict) else None
    artifacts = [
        ArtifactRecord(**a) if isinstance(a, dict) else a
        for a in data.get("artifacts", [])
    ]
    return ExperimentRunRecord(
        run_id=data["run_id"],
        name=data["name"],
        created_at_unix=float(data["created_at_unix"]),
        azmqos_version=data.get("azmqos_version", "2.7.0"),
        run_type=data.get("run_type", "generic"),
        status=data.get("status", "created"),
        tags=list(data.get("tags", [])),
        parameters=dict(data.get("parameters", {})),
        metrics=dict(data.get("metrics", {})),
        backend=backend,
        artifacts=artifacts,
        notes=data.get("notes"),
        metadata=dict(data.get("metadata", {})),
    )


def export_run_table_csv(records: list[ExperimentRunRecord], path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "run_id", "name", "created_at_unix", "run_type", "status", "tags",
            "backend_name", "job_id", "job_status", "artifact_count", "metrics_json"
        ])
        for r in records:
            writer.writerow([
                r.run_id,
                r.name,
                r.created_at_unix,
                r.run_type,
                r.status,
                ",".join(r.tags),
                r.backend.backend_name if r.backend else "",
                r.backend.job_id if r.backend else "",
                r.backend.job_status if r.backend else "",
                len(r.artifacts),
                json.dumps(r.metrics, default=str),
            ])
    return path


def export_dashboard_json(records: list[ExperimentRunRecord], path):
    path = Path(path)
    payload = {
        "generated_at_unix": time.time(),
        "run_count": len(records),
        "runs": [r.to_dict() for r in records],
        "summary": summarize_records(records),
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def summarize_records(records: list[ExperimentRunRecord]) -> dict[str, Any]:
    by_type = {}
    by_status = {}
    by_backend = {}
    metrics = {}

    for r in records:
        by_type[r.run_type] = by_type.get(r.run_type, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.backend and r.backend.backend_name:
            by_backend[r.backend.backend_name] = by_backend.get(r.backend.backend_name, 0) + 1
        for k, v in r.metrics.items():
            metrics.setdefault(k, []).append(float(v))

    metric_summary = {}
    for k, vals in metrics.items():
        metric_summary[k] = {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": sum(vals) / len(vals),
        }

    return {
        "by_type": by_type,
        "by_status": by_status,
        "by_backend": by_backend,
        "metrics": metric_summary,
    }


def make_run_database_report(records: list[ExperimentRunRecord], output_path):
    output_path = Path(output_path)
    summary = summarize_records(records)
    lines = [
        "# AZM-QOS v2.7 Experiment Database Report",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, indent=2, default=str),
        "```",
        "",
        "## Runs",
        "",
    ]
    for r in records:
        lines.extend([
            f"### {r.name}",
            "",
            "```text",
            r.summary(),
            "```",
            "",
        ])
        if r.backend:
            lines.extend(["Backend:", "", "```text", r.backend.summary(), "```", ""])
        if r.artifacts:
            lines.append("Artifacts:")
            lines.append("")
            for artifact in r.artifacts:
                lines.append(f"- `{artifact.name}`: `{artifact.path}`")
            lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def index_artifacts_from_directory(directory, run_name: str = "artifact_index", run_type: str = "artifact_index"):
    directory = Path(directory)
    artifacts = [artifact_from_path(p) for p in sorted(directory.rglob("*")) if p.is_file()]
    return new_run_record(
        name=run_name,
        run_type=run_type,
        status="indexed",
        tags=["artifacts"],
        artifacts=artifacts,
        parameters={"directory": str(directory)},
        metrics={"artifact_count": float(len(artifacts))},
    )


def create_demo_run_database(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = ExperimentDatabase(output_dir / "azmqos_runs.jsonl")

    # Demo simulator run
    sim_artifact = output_dir / "simulator_counts.json"
    sim_artifact.write_text(json.dumps({"00": 510, "11": 514}, indent=2), encoding="utf-8")
    sim_record = new_run_record(
        name="demo_simulator_counts",
        run_type="simulator",
        status="completed",
        tags=["simulator", "counts"],
        parameters={"shots": 1024},
        metrics={"expectation": 1.0, "shots": 1024.0},
        artifacts=[artifact_from_path(sim_artifact, artifact_type="counts_json")],
        notes="Demo simulator count result.",
    )
    db.append(sim_record)

    # Demo hardware run
    hw_artifact = output_dir / "hardware_counts.json"
    hw_artifact.write_text(json.dumps({"00": 470, "01": 30, "10": 34, "11": 490}, indent=2), encoding="utf-8")
    hw_record = new_run_record(
        name="demo_hardware_counts",
        run_type="hardware",
        status="completed",
        tags=["hardware", "ibm", "counts"],
        parameters={"shots": 1024},
        metrics={"expectation": 0.875, "shots": 1024.0, "tvd": 0.0625},
        backend=BackendMetadataRecord(
            backend_name="mock_ibm_backend",
            num_qubits=127,
            job_id="mock_job_id",
            job_status="DONE",
            timestamp_unix=time.time(),
            calibration_timestamp="mock_timestamp",
        ),
        artifacts=[artifact_from_path(hw_artifact, artifact_type="counts_json")],
        notes="Demo hardware-style count result.",
    )
    db.append(hw_record)

    records = db.read_all()
    artifacts = {}
    artifacts["run_table_csv"] = str(export_run_table_csv(records, output_dir / "run_table.csv"))
    artifacts["dashboard_json"] = str(export_dashboard_json(records, output_dir / "dashboard.json"))
    artifacts["markdown_report"] = str(make_run_database_report(records, output_dir / "run_database_report.md"))

    return db, records, artifacts
