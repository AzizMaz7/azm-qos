from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import time

from .qec_logical import StabilizerCodeSpec, get_code_by_name
from .qec_fault_tolerant import (
    CircuitNoiseModel,
    SyndromeExtractionCircuitSpec,
    make_repeated_syndrome_schedule,
    syndrome_spec_to_qiskit,
    run_production_ft_qec,
)
from .production import load_production_spec
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
class BackendTargetSpec:
    backend_name: str = "ibm_fez"
    max_qubits: int = 127
    max_depth: int = 5000
    max_cx_count: int = 2000
    native_gates: list[str] = field(default_factory=lambda: ["rz", "sx", "x", "cx", "measure", "reset"])
    coupling_model: str = "heavy_hex_scaffold"
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "BackendTargetSpec\n"
            f"  backend_name: {self.backend_name}\n"
            f"  max_qubits: {self.max_qubits}\n"
            f"  max_depth: {self.max_depth}\n"
            f"  max_cx_count: {self.max_cx_count}\n"
            f"  native_gates: {self.native_gates}\n"
            f"  coupling_model: {self.coupling_model}"
        )


@dataclass
class CircuitResourceSummary:
    circuit_id: str
    code_name: str
    round_index: int
    stabilizer_index: int
    n_qubits: int
    depth: int
    size: int
    cx_count: int
    measurement_count: int
    reset_count: int
    qiskit_available: bool
    transpiled: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "CircuitResourceSummary\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  code: {self.code_name}\n"
            f"  round: {self.round_index}\n"
            f"  stabilizer: {self.stabilizer_index}\n"
            f"  n_qubits: {self.n_qubits}\n"
            f"  depth: {self.depth}\n"
            f"  size: {self.size}\n"
            f"  cx_count: {self.cx_count}\n"
            f"  qiskit_available: {self.qiskit_available}\n"
            f"  transpiled: {self.transpiled}"
        )


@dataclass
class ISACheckResult:
    circuit_id: str
    backend_name: str
    passed: bool
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ISACheckResult\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  backend_name: {self.backend_name}\n"
            f"  passed: {self.passed}\n"
            f"  reasons: {self.reasons}"
        )


@dataclass
class LayoutRecommendation:
    code_name: str
    backend_name: str
    physical_qubits: list[int]
    ancilla_qubits: list[int]
    score: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "LayoutRecommendation\n"
            f"  code: {self.code_name}\n"
            f"  backend: {self.backend_name}\n"
            f"  physical_qubits: {self.physical_qubits}\n"
            f"  ancilla_qubits: {self.ancilla_qubits}\n"
            f"  score: {self.score:.6f}\n"
            f"  reason: {self.reason}"
        )


@dataclass
class HardwareDryRunJobManifest:
    job_id: str
    backend_name: str
    circuit_id: str
    shots: int
    status: str = "DRY_RUN_PREPARED"
    submitted: bool = False
    resource_summary: CircuitResourceSummary | None = None
    isa_check: ISACheckResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "HardwareDryRunJobManifest\n"
            f"  job_id: {self.job_id}\n"
            f"  backend: {self.backend_name}\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  shots: {self.shots}\n"
            f"  status: {self.status}\n"
            f"  submitted: {self.submitted}"
        )


@dataclass
class ProductionQECHardwareResult:
    project_name: str
    backend: BackendTargetSpec
    code: StabilizerCodeSpec
    layout: LayoutRecommendation
    resources: list[CircuitResourceSummary]
    isa_checks: list[ISACheckResult]
    job_manifests: list[HardwareDryRunJobManifest]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        passed = sum(1 for x in self.isa_checks if x.passed)
        return (
            "ProductionQECHardwareResult\n"
            f"  project: {self.project_name}\n"
            f"  backend: {self.backend.backend_name}\n"
            f"  code: {self.code.name}\n"
            f"  circuits: {len(self.resources)}\n"
            f"  isa_passed: {passed}/{len(self.isa_checks)}\n"
            f"  dry_run_jobs: {len(self.job_manifests)}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def qiskit_available() -> bool:
    try:
        import qiskit  # noqa: F401
        return True
    except Exception:
        return False


def default_backend_target(backend_name: str = "ibm_fez") -> BackendTargetSpec:
    key = str(backend_name).lower()
    if "fez" in key or "marrakesh" in key:
        return BackendTargetSpec(backend_name=backend_name, max_qubits=156, max_depth=7000, max_cx_count=3000)
    if "brisbane" in key or "kyiv" in key or "sherbrooke" in key:
        return BackendTargetSpec(backend_name=backend_name, max_qubits=127, max_depth=5000, max_cx_count=2500)
    return BackendTargetSpec(backend_name=backend_name)


def _operation_counts_from_spec(spec: SyndromeExtractionCircuitSpec) -> dict[str, int]:
    counts = {}
    for op in spec.operations:
        gate = str(op.get("gate", "")).lower()
        counts[gate] = counts.get(gate, 0) + 1
    return counts


def resource_summary_from_spec(
    spec: SyndromeExtractionCircuitSpec,
    optimization_level: int = 1,
) -> CircuitResourceSummary:
    counts = _operation_counts_from_spec(spec)
    n_qubits = max([spec.ancilla_qubit] + spec.data_qubits) + 1
    size = len(spec.operations)
    cx = counts.get("cx", 0)
    # Conservative fallback depth model.
    depth = max(1, size - max(0, optimization_level))
    return CircuitResourceSummary(
        circuit_id=spec.circuit_id,
        code_name=spec.code_name,
        round_index=spec.round_index,
        stabilizer_index=spec.stabilizer_index,
        n_qubits=n_qubits,
        depth=depth,
        size=size,
        cx_count=cx,
        measurement_count=counts.get("measure", 0),
        reset_count=counts.get("reset", 0),
        qiskit_available=False,
        transpiled=False,
        metadata={"source": "spec_fallback", "operation_counts": counts},
    )


def transpile_syndrome_spec_dry_run(
    spec: SyndromeExtractionCircuitSpec,
    backend: BackendTargetSpec,
    optimization_level: int = 1,
) -> CircuitResourceSummary:
    try:
        from qiskit import transpile
        qc = syndrome_spec_to_qiskit(spec)
        tqc = transpile(qc, basis_gates=backend.native_gates, optimization_level=optimization_level)
        ops = dict(tqc.count_ops())
        return CircuitResourceSummary(
            circuit_id=spec.circuit_id,
            code_name=spec.code_name,
            round_index=spec.round_index,
            stabilizer_index=spec.stabilizer_index,
            n_qubits=tqc.num_qubits,
            depth=int(tqc.depth()),
            size=int(tqc.size()),
            cx_count=int(ops.get("cx", 0)),
            measurement_count=int(ops.get("measure", 0)),
            reset_count=int(ops.get("reset", 0)),
            qiskit_available=True,
            transpiled=True,
            metadata={
                "basis_gates": backend.native_gates,
                "optimization_level": optimization_level,
                "operation_counts": {str(k): int(v) for k, v in ops.items()},
                "qasm_or_text": str(tqc),
            },
        )
    except Exception as exc:
        summary = resource_summary_from_spec(spec, optimization_level=optimization_level)
        summary.metadata["qiskit_error"] = str(exc)
        return summary


def check_isa_constraints(summary: CircuitResourceSummary, backend: BackendTargetSpec) -> ISACheckResult:
    reasons = []
    if summary.n_qubits > backend.max_qubits:
        reasons.append(f"n_qubits {summary.n_qubits} exceeds backend max {backend.max_qubits}")
    if summary.depth > backend.max_depth:
        reasons.append(f"depth {summary.depth} exceeds backend max {backend.max_depth}")
    if summary.cx_count > backend.max_cx_count:
        reasons.append(f"cx_count {summary.cx_count} exceeds backend max {backend.max_cx_count}")
    if summary.measurement_count <= 0:
        reasons.append("circuit has no measurement")
    if summary.reset_count <= 0:
        reasons.append("circuit has no ancilla reset")
    return ISACheckResult(
        circuit_id=summary.circuit_id,
        backend_name=backend.backend_name,
        passed=len(reasons) == 0,
        reasons=reasons,
        metadata={"resource_summary": asdict(summary)},
    )


def recommend_noise_aware_layout(
    code: StabilizerCodeSpec,
    backend: BackendTargetSpec,
    noise_model: CircuitNoiseModel | None = None,
) -> LayoutRecommendation:
    noise_model = noise_model or CircuitNoiseModel()
    n_data = code.n_physical
    n_anc = len(code.stabilizers)
    physical = list(range(n_data))
    ancilla = list(range(n_data, n_data + n_anc))
    penalty = (
        noise_model.data_error_rate
        + noise_model.measurement_error_rate
        + noise_model.two_qubit_error_rate
        + noise_model.idle_error_rate
    )
    compactness = 1.0 / max(1, n_data + n_anc)
    score = max(0.0, 1.0 - penalty) * compactness
    return LayoutRecommendation(
        code_name=code.name,
        backend_name=backend.backend_name,
        physical_qubits=physical,
        ancilla_qubits=ancilla,
        score=score,
        reason="Compact contiguous scaffold layout minimizing data/ancilla span.",
        metadata={"noise_model": asdict(noise_model), "coupling_model": backend.coupling_model},
    )


def make_hardware_dry_run_job_manifest(
    summary: CircuitResourceSummary,
    isa: ISACheckResult,
    backend: BackendTargetSpec,
    shots: int,
) -> HardwareDryRunJobManifest:
    digest = hashlib.sha256(f"{summary.circuit_id}|{backend.backend_name}|{shots}|{summary.depth}".encode("utf-8")).hexdigest()[:12]
    return HardwareDryRunJobManifest(
        job_id=f"AZMQOS-DRYRUN-{digest}",
        backend_name=backend.backend_name,
        circuit_id=summary.circuit_id,
        shots=shots,
        status="DRY_RUN_READY" if isa.passed else "DRY_RUN_NEEDS_REVIEW",
        submitted=False,
        resource_summary=summary,
        isa_check=isa,
        metadata={
            "created_at_unix": time.time(),
            "message": "Dry-run manifest only. No hardware job submitted.",
        },
    )


def export_resource_summaries_csv(items: list[CircuitResourceSummary], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["circuit_id", "code_name", "round_index", "stabilizer_index", "n_qubits", "depth", "size", "cx_count", "measurement_count", "reset_count", "qiskit_available", "transpiled"])
        for x in items:
            writer.writerow([x.circuit_id, x.code_name, x.round_index, x.stabilizer_index, x.n_qubits, x.depth, x.size, x.cx_count, x.measurement_count, x.reset_count, x.qiskit_available, x.transpiled])
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


def export_isa_checks_csv(items: list[ISACheckResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["circuit_id", "backend_name", "passed", "reasons"])
        for x in items:
            writer.writerow([x.circuit_id, x.backend_name, x.passed, json.dumps(x.reasons)])
    return path


def export_job_manifests_csv(items: list[HardwareDryRunJobManifest], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        import csv
        writer = csv.writer(f)
        writer.writerow(["job_id", "backend_name", "circuit_id", "shots", "status", "submitted"])
        for x in items:
            writer.writerow([x.job_id, x.backend_name, x.circuit_id, x.shots, x.status, x.submitted])
    return path


def plot_resource_summaries(items: list[CircuitResourceSummary], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(x.summary() for x in items), encoding="utf-8")
        return txt

    labels = [x.circuit_id for x in items]
    depths = [x.depth for x in items]
    cxs = [x.cx_count for x in items]
    xvals = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(xvals, depths, marker="o", label="depth")
    ax.plot(xvals, cxs, marker="s", label="CX count")
    ax.set_xlabel("syndrome circuit")
    ax.set_ylabel("resource count")
    ax.set_title("QEC syndrome circuit resources")
    if len(labels) <= 12:
        ax.set_xticks(xvals)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def attach_hardware_dry_run_to_database(spec, manifests: list[HardwareDryRunJobManifest], database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    records = []
    for item in manifests:
        resources = item.resource_summary
        isa = item.isa_check
        artifacts = [
            artifact_from_path(path, name=name, artifact_type="qec_hardware_dry_run_artifact")
            for name, path in artifact_paths.items()
        ]
        record = new_run_record(
            name=f"qec_hardware_{item.circuit_id}",
            run_type="qec_hardware_dry_run",
            status=item.status,
            tags=["qec", "hardware_dry_run", item.backend_name],
            parameters={
                "circuit_id": item.circuit_id,
                "backend_name": item.backend_name,
                "shots": item.shots,
                "submitted": item.submitted,
            },
            metrics={
                "n_qubits": float(resources.n_qubits if resources else 0),
                "depth": float(resources.depth if resources else 0),
                "size": float(resources.size if resources else 0),
                "cx_count": float(resources.cx_count if resources else 0),
                "isa_passed": float(1 if isa and isa.passed else 0),
            },
            backend=BackendMetadataRecord(
                backend_name=item.backend_name,
                job_id=item.job_id,
                job_status=item.status,
                timestamp_unix=time.time(),
            ),
            artifacts=artifacts,
            notes="QEC hardware dry-run manifest. No hardware job submitted.",
        )
        db.append(record)
        records.append(record)
    return db, records


def make_qec_hardware_report(result: ProductionQECHardwareResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.4 Hardware-Ready QEC Transpilation Report",
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
        "## Layout recommendation",
        "",
        "```text",
        result.layout.summary(),
        "```",
        "",
        "## Circuit resources",
        "",
    ]
    for x in result.resources:
        lines.extend(["```text", x.summary(), "```", ""])
    lines.extend(["## ISA checks", ""])
    for x in result.isa_checks:
        lines.extend(["```text", x.summary(), "```", ""])
    lines.extend(["## Dry-run job manifests", ""])
    for x in result.job_manifests:
        lines.extend(["```text", x.summary(), "```", ""])
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
        "This workflow creates hardware dry-run manifests only. No IBM Runtime job is submitted.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_qec_hardware_demo(output_dir, backend_name: str = "ibm_fez", code_name: str = "repetition3", rounds: int = 3, shots: int = 64):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    backend = default_backend_target(backend_name)
    code = get_code_by_name(code_name)
    noise = CircuitNoiseModel()
    schedule = make_repeated_syndrome_schedule(code, rounds=rounds)
    layout = recommend_noise_aware_layout(code, backend, noise)

    resources = [transpile_syndrome_spec_dry_run(spec, backend) for spec in schedule]
    isa = [check_isa_constraints(x, backend) for x in resources]
    manifests = [make_hardware_dry_run_job_manifest(r, i, backend, shots) for r, i in zip(resources, isa)]

    artifacts = {}
    artifacts["syndrome_circuit_specs_json"] = str(export_json_dataclasses(schedule, output_dir / "syndrome_circuit_specs.json"))
    artifacts["resource_summaries_csv"] = str(export_resource_summaries_csv(resources, output_dir / "resource_summaries.csv"))
    artifacts["resource_summaries_json"] = str(export_json_dataclasses(resources, output_dir / "resource_summaries.json"))
    artifacts["isa_checks_csv"] = str(export_isa_checks_csv(isa, output_dir / "isa_checks.csv"))
    artifacts["isa_checks_json"] = str(export_json_dataclasses(isa, output_dir / "isa_checks.json"))
    artifacts["job_manifests_csv"] = str(export_job_manifests_csv(manifests, output_dir / "job_manifests.csv"))
    artifacts["job_manifests_json"] = str(export_json_dataclasses(manifests, output_dir / "job_manifests.json"))
    artifacts["layout_recommendation_json"] = str(export_json_dataclasses(layout, output_dir / "layout_recommendation.json"))
    artifacts["resource_figure"] = str(plot_resource_summaries(resources, output_dir / "resource_summaries.png"))

    result = ProductionQECHardwareResult(
        project_name="qec_hardware_demo",
        backend=backend,
        code=code,
        layout=layout,
        resources=resources,
        isa_checks=isa,
        job_manifests=manifests,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )
    artifacts["hardware_report"] = str(make_qec_hardware_report(result, output_dir / "qec_hardware_report.md"))

    manifest_path = output_dir / "qec_hardware_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.4 QEC hardware dry-run demo",
        "summary": result.summary(),
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionQECHardwareResult(
        project_name="qec_hardware_demo",
        backend=backend,
        code=code,
        layout=layout,
        resources=resources,
        isa_checks=isa,
        job_manifests=manifests,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )


def run_production_qec_hardware_dry_run(
    spec_or_path,
    backend_name: str = "ibm_fez",
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    rounds: int = 3,
    physical_error_rate: float = 0.01,
    measurement_error_rate: float = 0.02,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir) / "qec_hardware_dry_run"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run FT-QEC base workflow first so the dry-run is tied to production estimates.
    ft = run_production_ft_qec(
        spec,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        rounds=rounds,
        physical_error_rate=physical_error_rate,
        measurement_error_rate=measurement_error_rate,
    )

    backend = default_backend_target(backend_name)
    code = get_code_by_name(code_name)
    noise = ft.noise_model
    schedule = make_repeated_syndrome_schedule(code, rounds=rounds)
    layout = recommend_noise_aware_layout(code, backend, noise)

    resources = [transpile_syndrome_spec_dry_run(spec_item, backend) for spec_item in schedule]
    isa = [check_isa_constraints(x, backend) for x in resources]
    manifests = [make_hardware_dry_run_job_manifest(r, i, backend, shots) for r, i in zip(resources, isa)]

    artifacts = {}
    artifacts["syndrome_circuit_specs_json"] = str(export_json_dataclasses(schedule, output_dir / "syndrome_circuit_specs.json"))
    artifacts["resource_summaries_csv"] = str(export_resource_summaries_csv(resources, output_dir / "resource_summaries.csv"))
    artifacts["resource_summaries_json"] = str(export_json_dataclasses(resources, output_dir / "resource_summaries.json"))
    artifacts["isa_checks_csv"] = str(export_isa_checks_csv(isa, output_dir / "isa_checks.csv"))
    artifacts["isa_checks_json"] = str(export_json_dataclasses(isa, output_dir / "isa_checks.json"))
    artifacts["job_manifests_csv"] = str(export_job_manifests_csv(manifests, output_dir / "job_manifests.csv"))
    artifacts["job_manifests_json"] = str(export_json_dataclasses(manifests, output_dir / "job_manifests.json"))
    artifacts["layout_recommendation_json"] = str(export_json_dataclasses(layout, output_dir / "layout_recommendation.json"))
    artifacts["resource_figure"] = str(plot_resource_summaries(resources, output_dir / "resource_summaries.png"))

    db, records = attach_hardware_dry_run_to_database(
        spec=spec,
        manifests=manifests,
        database_path=Path(spec.output_dir) / "database" / "qec_hardware_dry_runs.jsonl",
        artifact_paths={
            "resource_summaries_csv": artifacts["resource_summaries_csv"],
            "isa_checks_csv": artifacts["isa_checks_csv"],
            "job_manifests_json": artifacts["job_manifests_json"],
        },
    )
    artifacts["hardware_database_jsonl"] = str(db.path)
    artifacts["hardware_run_table_csv"] = str(export_run_table_csv(records, Path(spec.output_dir) / "database" / "qec_hardware_run_table.csv"))
    artifacts["hardware_dashboard_json"] = str(export_dashboard_json(records, Path(spec.output_dir) / "database" / "qec_hardware_dashboard.json"))
    artifacts["hardware_database_report"] = str(make_run_database_report(records, Path(spec.output_dir) / "database" / "qec_hardware_database_report.md"))

    dashboard = build_dashboard_package(Path(spec.output_dir) / "dashboard_qec_hardware", database_path=db.path)
    artifacts["hardware_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["hardware_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")

    result = ProductionQECHardwareResult(
        project_name=spec.project_name,
        backend=backend,
        code=code,
        layout=layout,
        resources=resources,
        isa_checks=isa,
        job_manifests=manifests,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(ft.warnings),
        metadata={"base_ft_qec_artifacts": ft.artifacts, "rounds": rounds},
    )
    artifacts["hardware_report"] = str(make_qec_hardware_report(result, output_dir / "qec_hardware_report.md"))

    manifest_path = output_dir / "production_qec_hardware_dry_run_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.4 production QEC hardware dry-run",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": result.warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionQECHardwareResult(
        project_name=spec.project_name,
        backend=backend,
        code=code,
        layout=layout,
        resources=resources,
        isa_checks=isa,
        job_manifests=manifests,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(ft.warnings),
        metadata={"base_ft_qec_artifacts": ft.artifacts, "rounds": rounds},
    )
