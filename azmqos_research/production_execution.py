from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import math
import random
import time
import uuid

from .production import (
    ProductionProjectSpec,
    ProductionPlan,
    ProductionPlanItem,
    load_production_spec,
    make_production_plan,
    export_production_plan_json,
    export_production_plan_csv,
    make_production_plan_report,
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
class WorkloadSpec:
    workload_id: str
    plan_id: str
    component_name: str
    quantity: str
    family: str | None
    indices: list[int]
    n_terms: int
    measurement_type: str
    shots: int
    backend_name: str | None
    execution_mode: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "WorkloadSpec\n"
            f"  workload_id: {self.workload_id}\n"
            f"  component_name: {self.component_name}\n"
            f"  family: {self.family}\n"
            f"  quantity: {self.quantity}\n"
            f"  measurement_type: {self.measurement_type}\n"
            f"  shots: {self.shots}\n"
            f"  mode: {self.execution_mode}"
        )


@dataclass
class ExecutionResult:
    workload_id: str
    plan_id: str
    component_name: str
    status: str
    estimate: float | None = None
    counts: dict[str, int] | None = None
    job_id: str | None = None
    backend_name: str | None = None
    execution_mode: str = "simulator"
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ExecutionResult\n"
            f"  workload_id: {self.workload_id}\n"
            f"  component_name: {self.component_name}\n"
            f"  status: {self.status}\n"
            f"  estimate: {self.estimate}\n"
            f"  job_id: {self.job_id}\n"
            f"  backend_name: {self.backend_name}\n"
            f"  mode: {self.execution_mode}"
        )


@dataclass
class JobManifest:
    manifest_id: str
    project_name: str
    created_at_unix: float
    execution_mode: str
    backend_name: str | None
    workloads: list[WorkloadSpec]
    dry_run: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "JobManifest\n"
            f"  manifest_id: {self.manifest_id}\n"
            f"  project_name: {self.project_name}\n"
            f"  execution_mode: {self.execution_mode}\n"
            f"  backend_name: {self.backend_name}\n"
            f"  workloads: {len(self.workloads)}\n"
            f"  dry_run: {self.dry_run}"
        )


@dataclass
class ProductionExecutionBatchResult:
    spec: ProductionProjectSpec
    plan: ProductionPlan
    workloads: list[WorkloadSpec]
    job_manifest: JobManifest
    results: list[ExecutionResult]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        by_status = {}
        for result in self.results:
            by_status[result.status] = by_status.get(result.status, 0) + 1
        return (
            "ProductionExecutionBatchResult\n"
            f"  project: {self.spec.project_name}\n"
            f"  workloads: {len(self.workloads)}\n"
            f"  results: {len(self.results)}\n"
            f"  by_status: {by_status}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def classify_measurement_type(family: str | None, quantity: str) -> str:
    if quantity == "M":
        if family in {"Mbb", "Mab", "Maa", "Mba"}:
            return "metric_matrix_element"
        return "metric_observable"
    if quantity == "V":
        if family in {"Va", "Vb"}:
            return "gradient_vector_element"
        return "gradient_observable"
    return "generic_observable"


def plan_item_to_workload(item: ProductionPlanItem, spec: ProductionProjectSpec) -> WorkloadSpec:
    return WorkloadSpec(
        workload_id=str(uuid.uuid4()),
        plan_id=item.plan_id,
        component_name=item.component_name,
        quantity=item.quantity,
        family=item.family,
        indices=list(item.indices),
        n_terms=item.n_terms,
        measurement_type=classify_measurement_type(item.family, item.quantity),
        shots=spec.execution_policy.shots,
        backend_name=spec.execution_policy.backend_name,
        execution_mode=spec.execution_policy.mode,
        metadata={
            "repeats": spec.execution_policy.repeats,
            "optimization_level": spec.execution_policy.optimization_level,
            "allow_hardware_submit": spec.execution_policy.allow_hardware_submit,
        },
    )


def production_plan_to_workloads(plan: ProductionPlan, spec: ProductionProjectSpec) -> list[WorkloadSpec]:
    return [plan_item_to_workload(item, spec) for item in plan.items]


def make_job_manifest(spec: ProductionProjectSpec, workloads: list[WorkloadSpec], dry_run: bool = True) -> JobManifest:
    return JobManifest(
        manifest_id=str(uuid.uuid4()),
        project_name=spec.project_name,
        created_at_unix=time.time(),
        execution_mode=spec.execution_policy.mode,
        backend_name=spec.execution_policy.backend_name,
        workloads=workloads,
        dry_run=dry_run,
        metadata={
            "shots": spec.execution_policy.shots,
            "repeats": spec.execution_policy.repeats,
            "queue_policy": {
                "max_jobs_per_batch": spec.queue_policy.max_jobs_per_batch,
                "poll_interval_seconds": spec.queue_policy.poll_interval_seconds,
                "auto_resume": spec.queue_policy.auto_resume,
                "fail_fast": spec.queue_policy.fail_fast,
            },
        },
    )


def _stable_float_from_text(text: str, low: float = -1.0, high: float = 1.0) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    intval = int(digest[:12], 16)
    unit = intval / float(16 ** 12 - 1)
    return low + (high - low) * unit


def _estimate_to_counts(estimate: float, shots: int) -> dict[str, int]:
    # Map expectation-like value in [-1,1] to binary counts.
    p0 = max(0.0, min(1.0, 0.5 * (1.0 + estimate)))
    n0 = int(round(p0 * shots))
    n1 = max(0, shots - n0)
    return {"0": n0, "1": n1}


def simulate_workload_result(workload: WorkloadSpec, seed: int | None = 123) -> ExecutionResult:
    base = _stable_float_from_text(
        f"{workload.component_name}|{workload.quantity}|{workload.family}|{workload.indices}|{workload.n_terms}"
    )
    # Make placeholder/template terms small but deterministic.
    scale = 1.0 / max(1.0, math.sqrt(max(1, workload.n_terms)))
    estimate = max(-1.0, min(1.0, base * scale))
    counts = _estimate_to_counts(estimate, workload.shots)
    return ExecutionResult(
        workload_id=workload.workload_id,
        plan_id=workload.plan_id,
        component_name=workload.component_name,
        status="completed",
        estimate=estimate,
        counts=counts,
        job_id=None,
        backend_name=workload.backend_name,
        execution_mode="simulator",
        message="Deterministic local simulator-adapter placeholder result.",
        metadata={
            "measurement_type": workload.measurement_type,
            "n_terms": workload.n_terms,
            "seed": seed,
        },
    )


def run_simulator_batch(workloads: list[WorkloadSpec], seed: int | None = 123) -> list[ExecutionResult]:
    return [simulate_workload_result(workload, seed=seed) for workload in workloads]


def run_hardware_dry_run_batch(workloads: list[WorkloadSpec]) -> list[ExecutionResult]:
    results = []
    for workload in workloads:
        pseudo_job_id = "DRYRUN-" + hashlib.sha256(workload.workload_id.encode("utf-8")).hexdigest()[:12]
        results.append(
            ExecutionResult(
                workload_id=workload.workload_id,
                plan_id=workload.plan_id,
                component_name=workload.component_name,
                status="dry_run_prepared",
                estimate=None,
                counts=None,
                job_id=pseudo_job_id,
                backend_name=workload.backend_name,
                execution_mode="hardware_dry_run",
                message="Hardware dry-run manifest prepared. No IBM job submitted.",
                metadata={
                    "measurement_type": workload.measurement_type,
                    "shots": workload.shots,
                    "n_terms": workload.n_terms,
                },
            )
        )
    return results


def export_job_manifest_json(manifest: JobManifest, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(manifest)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def export_workloads_csv(workloads: list[WorkloadSpec], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "workload_id", "plan_id", "component_name", "quantity", "family", "indices",
            "n_terms", "measurement_type", "shots", "backend_name", "execution_mode"
        ])
        for w in workloads:
            writer.writerow([
                w.workload_id,
                w.plan_id,
                w.component_name,
                w.quantity,
                w.family,
                json.dumps(w.indices),
                w.n_terms,
                w.measurement_type,
                w.shots,
                w.backend_name,
                w.execution_mode,
            ])
    return path


def export_execution_results_json(results: list[ExecutionResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(r) for r in results], indent=2, default=str), encoding="utf-8")
    return path


def export_execution_results_csv(results: list[ExecutionResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "workload_id", "plan_id", "component_name", "status", "estimate",
            "counts_json", "job_id", "backend_name", "execution_mode", "message"
        ])
        for r in results:
            writer.writerow([
                r.workload_id,
                r.plan_id,
                r.component_name,
                r.status,
                r.estimate,
                json.dumps(r.counts or {}),
                r.job_id,
                r.backend_name,
                r.execution_mode,
                r.message,
            ])
    return path


def attach_results_to_production_database(
    spec: ProductionProjectSpec,
    plan: ProductionPlan,
    workloads: list[WorkloadSpec],
    results: list[ExecutionResult],
    database_path,
    artifact_paths: dict[str, str] | None = None,
):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    result_by_plan = {r.plan_id: r for r in results}
    workload_by_plan = {w.plan_id: w for w in workloads}

    records = []
    for item in plan.items:
        result = result_by_plan.get(item.plan_id)
        workload = workload_by_plan.get(item.plan_id)
        status = result.status if result else "missing_result"
        metrics = {
            "n_terms": float(item.n_terms),
            "shots": float(spec.execution_policy.shots),
        }
        if result and result.estimate is not None:
            metrics["estimate"] = float(result.estimate)
        if result and result.counts:
            metrics["total_counts"] = float(sum(result.counts.values()))

        artifacts = []
        for name, path in artifact_paths.items():
            artifacts.append(artifact_from_path(path, name=name, artifact_type="execution_artifact"))

        record = new_run_record(
            name=f"execution_{item.component_name}",
            run_type="production_execution",
            status=status,
            tags=["production", "execution", item.family or "unknown", item.quantity],
            parameters={
                "component_name": item.component_name,
                "quantity": item.quantity,
                "indices": item.indices,
                "measurement_type": workload.measurement_type if workload else None,
                "execution_mode": result.execution_mode if result else spec.execution_policy.mode,
            },
            metrics=metrics,
            backend=BackendMetadataRecord(
                backend_name=result.backend_name if result else spec.execution_policy.backend_name,
                job_id=result.job_id if result else None,
                job_status=status,
                timestamp_unix=time.time(),
            ),
            artifacts=artifacts,
            notes=result.message if result else "No result attached.",
        )
        db.append(record)
        records.append(record)

    return db, records


def make_execution_report(batch: ProductionExecutionBatchResult, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AZM-QOS v3.2 Production Execution Report",
        "",
        "## Summary",
        "",
        "```text",
        batch.summary(),
        "```",
        "",
        "## Job manifest",
        "",
        "```text",
        batch.job_manifest.summary(),
        "```",
        "",
        "## Results",
        "",
    ]
    for result in batch.results:
        lines.extend(["```text", result.summary(), "```", ""])
    if batch.warnings:
        lines.extend(["## Warnings", ""])
        for warning in batch.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    lines.extend([
        "## Artifacts",
        "",
    ])
    for key, value in batch.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")
    lines.extend([
        "",
        "## Safety note",
        "",
        "Hardware execution in v3.2 is dry-run only. No IBM job is submitted by this adapter.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_production_execution_adapter(spec_or_path, force_mode: str | None = None) -> ProductionExecutionBatchResult:
    if isinstance(spec_or_path, (str, Path)):
        spec = load_production_spec(spec_or_path)
    else:
        spec = spec_or_path

    if force_mode is not None:
        spec.execution_policy.mode = force_mode

    output_dir = Path(spec.output_dir)
    execution_dir = output_dir / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)

    warnings = []
    if spec.execution_policy.allow_hardware_submit:
        warnings.append("allow_hardware_submit=True ignored by v3.2 execution adapter; hardware submission is blocked.")

    plan = make_production_plan(spec)
    workloads = production_plan_to_workloads(plan, spec)
    manifest = make_job_manifest(spec, workloads, dry_run=(spec.execution_policy.mode != "simulator"))

    artifacts = {}
    artifacts["production_plan_json"] = str(export_production_plan_json(plan, execution_dir / "production_plan.json"))
    artifacts["production_plan_csv"] = str(export_production_plan_csv(plan, execution_dir / "production_plan.csv"))
    artifacts["production_plan_report"] = str(make_production_plan_report(plan, execution_dir / "production_plan_report.md"))
    artifacts["workloads_csv"] = str(export_workloads_csv(workloads, execution_dir / "workloads.csv"))
    artifacts["job_manifest_json"] = str(export_job_manifest_json(manifest, execution_dir / "job_manifest.json"))

    if spec.execution_policy.mode == "simulator":
        results = run_simulator_batch(workloads)
    else:
        results = run_hardware_dry_run_batch(workloads)

    artifacts["execution_results_json"] = str(export_execution_results_json(results, execution_dir / "execution_results.json"))
    artifacts["execution_results_csv"] = str(export_execution_results_csv(results, execution_dir / "execution_results.csv"))

    db, records = attach_results_to_production_database(
        spec=spec,
        plan=plan,
        workloads=workloads,
        results=results,
        database_path=output_dir / "database" / "production_execution_runs.jsonl",
        artifact_paths={
            "execution_results_json": artifacts["execution_results_json"],
            "job_manifest_json": artifacts["job_manifest_json"],
        },
    )
    artifacts["execution_database_jsonl"] = str(db.path)
    artifacts["execution_run_table_csv"] = str(export_run_table_csv(records, output_dir / "database" / "execution_run_table.csv"))
    artifacts["execution_dashboard_json"] = str(export_dashboard_json(records, output_dir / "database" / "execution_dashboard.json"))
    artifacts["execution_database_report"] = str(make_run_database_report(records, output_dir / "database" / "execution_database_report.md"))

    dashboard = build_dashboard_package(output_dir / "dashboard_execution", database_path=db.path)
    artifacts["dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")
    artifacts["artifact_browser_html"] = dashboard.artifacts.get("artifact_browser_html", "")

    batch = ProductionExecutionBatchResult(
        spec=spec,
        plan=plan,
        workloads=workloads,
        job_manifest=manifest,
        results=results,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings + plan.warnings,
    )

    artifacts["execution_report"] = str(make_execution_report(batch, execution_dir / "production_execution_report.md"))

    manifest_payload = {
        "package": "AZM-QOS v3.2 production execution adapters",
        "summary": batch.summary(),
        "warnings": batch.warnings,
        "artifacts": artifacts,
    }
    manifest_path = execution_dir / "production_execution_manifest.json"
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, default=str), encoding="utf-8")
    artifacts["production_execution_manifest"] = str(manifest_path)

    return ProductionExecutionBatchResult(
        spec=spec,
        plan=plan,
        workloads=workloads,
        job_manifest=manifest,
        results=results,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings + plan.warnings,
    )
