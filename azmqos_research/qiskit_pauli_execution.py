from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable
import csv
import hashlib
import itertools
import json
import math
import time

from .production import ProductionProjectSpec, load_production_spec
from .pauli_compiler import (
    PauliComponent,
    CommutingGroup,
    MeasurementCircuitSpec,
    PauliCompilationResult,
    compile_pauli_component,
    measurement_circuit_spec_from_group,
    expectation_from_counts_for_pauli,
    can_share_single_qubit_measurement_basis,
)
from .production_pauli_execution import (
    ComponentEstimateResult,
    GroupedMeasurementResult,
    load_selected_pauli_components,
    deterministic_counts_for_basis,
    reconstruct_component_estimate,
    export_grouped_counts_json,
    export_grouped_counts_csv,
    export_component_estimates_csv,
    export_mv_estimate_tables,
    plot_component_estimates,
    attach_pauli_estimates_to_database,
    make_mv_estimate_report,
    make_production_pauli_execution_report,
    ProductionPauliExecutionResult,
)
from .experiment_db import export_run_table_csv, export_dashboard_json, make_run_database_report
from .dashboard import build_dashboard_package


@dataclass
class QiskitExecutionConfig:
    backend: str = "auto"  # auto, aer, basic, fallback, hardware_dry_run
    shots: int = 1024
    seed: int | None = 123
    optimization_level: int = 1
    reverse_bitstrings: bool = True
    use_qiskit_if_available: bool = True
    hardware_backend_name: str | None = None

    def summary(self) -> str:
        return (
            "QiskitExecutionConfig\n"
            f"  backend: {self.backend}\n"
            f"  shots: {self.shots}\n"
            f"  seed: {self.seed}\n"
            f"  optimization_level: {self.optimization_level}\n"
            f"  reverse_bitstrings: {self.reverse_bitstrings}\n"
            f"  use_qiskit_if_available: {self.use_qiskit_if_available}\n"
            f"  hardware_backend_name: {self.hardware_backend_name}"
        )


@dataclass
class QiskitCircuitBuildResult:
    circuit_id: str
    group_id: str
    component_name: str
    measurement_basis: str
    n_qubits: int
    qiskit_available: bool
    circuit_repr: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "QiskitCircuitBuildResult\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  component_name: {self.component_name}\n"
            f"  group_id: {self.group_id}\n"
            f"  basis: {self.measurement_basis}\n"
            f"  n_qubits: {self.n_qubits}\n"
            f"  qiskit_available: {self.qiskit_available}"
        )


@dataclass
class QiskitGroupExecutionResult:
    component_name: str
    group_id: str
    measurement_basis: str
    backend_used: str
    status: str
    shots: int
    counts: dict[str, int]
    term_expectations: dict[str, float]
    circuit_build: QiskitCircuitBuildResult
    job_id: str | None = None
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_grouped_measurement_result(self) -> GroupedMeasurementResult:
        return GroupedMeasurementResult(
            component_name=self.component_name,
            group_id=self.group_id,
            measurement_basis=self.measurement_basis,
            shots=self.shots,
            counts=self.counts,
            term_expectations=self.term_expectations,
            metadata={
                "backend_used": self.backend_used,
                "status": self.status,
                "job_id": self.job_id,
                **self.metadata,
            },
        )

    def summary(self) -> str:
        return (
            "QiskitGroupExecutionResult\n"
            f"  component: {self.component_name}\n"
            f"  group_id: {self.group_id}\n"
            f"  basis: {self.measurement_basis}\n"
            f"  backend_used: {self.backend_used}\n"
            f"  status: {self.status}\n"
            f"  shots: {self.shots}\n"
            f"  job_id: {self.job_id}\n"
            f"  term_expectations: {self.term_expectations}"
        )


@dataclass
class QiskitComponentExecutionResult:
    component: PauliComponent
    compilation: PauliCompilationResult
    group_results: list[QiskitGroupExecutionResult]
    component_estimate: ComponentEstimateResult
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "QiskitComponentExecutionResult\n"
            f"  component: {self.component.name}\n"
            f"  groups: {len(self.group_results)}\n"
            f"  estimate: {self.component_estimate.estimate.real:+.10f}{self.component_estimate.estimate.imag:+.10f}j"
        )


@dataclass
class ProductionQiskitExecutionResult:
    spec: ProductionProjectSpec
    config: QiskitExecutionConfig
    components: list[PauliComponent]
    component_results: list[QiskitComponentExecutionResult]
    component_estimates: list[ComponentEstimateResult]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        backend_counts = {}
        for comp in self.component_results:
            for group in comp.group_results:
                backend_counts[group.backend_used] = backend_counts.get(group.backend_used, 0) + 1
        return (
            "ProductionQiskitExecutionResult\n"
            f"  project: {self.spec.project_name}\n"
            f"  components: {len(self.components)}\n"
            f"  estimates: {len(self.component_estimates)}\n"
            f"  backend_counts: {backend_counts}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def qiskit_is_available() -> bool:
    try:
        import qiskit  # noqa: F401
        return True
    except Exception:
        return False


def build_qiskit_measurement_circuit(
    spec: MeasurementCircuitSpec,
    state_preparation_hook: Callable[[Any], Any] | None = None,
):
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:
        raise ImportError("Qiskit is not installed. Install with: python -m pip install qiskit") from exc

    qc = QuantumCircuit(spec.n_qubits, spec.n_qubits)

    if state_preparation_hook is not None:
        state_preparation_hook(qc)
    else:
        # Deterministic nontrivial placeholder state preparation.
        for q, ch in enumerate(spec.measurement_basis):
            if ch != "I":
                angle = 0.25 + 0.17 * (q + 1)
                qc.ry(angle, q)

    for q, rot in spec.basis_rotations:
        if rot == "H":
            qc.h(q)
        elif rot == "SdgH":
            qc.sdg(q)
            qc.h(q)
        else:
            raise ValueError(f"Unknown basis rotation: {rot}")

    qc.measure(range(spec.n_qubits), range(spec.n_qubits))
    return qc


def build_circuit_or_fallback_spec(
    component: PauliComponent,
    group: CommutingGroup,
    state_preparation_hook: Callable[[Any], Any] | None = None,
) -> tuple[MeasurementCircuitSpec, QiskitCircuitBuildResult, Any | None]:
    spec = measurement_circuit_spec_from_group(group)
    try:
        qc = build_qiskit_measurement_circuit(spec, state_preparation_hook=state_preparation_hook)
        return spec, QiskitCircuitBuildResult(
            circuit_id=spec.circuit_id,
            group_id=group.group_id,
            component_name=component.name,
            measurement_basis=group.measurement_basis,
            n_qubits=spec.n_qubits,
            qiskit_available=True,
            circuit_repr=str(qc),
            metadata={"basis_rotations": spec.basis_rotations},
        ), qc
    except Exception as exc:
        return spec, QiskitCircuitBuildResult(
            circuit_id=spec.circuit_id,
            group_id=group.group_id,
            component_name=component.name,
            measurement_basis=group.measurement_basis,
            n_qubits=spec.n_qubits,
            qiskit_available=False,
            circuit_repr=f"FALLBACK_SPEC basis={group.measurement_basis} rotations={spec.basis_rotations}",
            metadata={"error": str(exc), "basis_rotations": spec.basis_rotations},
        ), None


def normalize_qiskit_counts(counts: dict[str, int], n_qubits: int, reverse_bitstrings: bool = True) -> dict[str, int]:
    normalized = {}
    for key, value in counts.items():
        bitstring = str(key).replace(" ", "")
        # Remove classical register labels if present in unusual formats.
        bitstring = bitstring.split()[-1] if " " in bitstring else bitstring
        if len(bitstring) < n_qubits:
            bitstring = bitstring.zfill(n_qubits)
        if len(bitstring) > n_qubits:
            bitstring = bitstring[-n_qubits:]
        if reverse_bitstrings:
            bitstring = bitstring[::-1]
        normalized[bitstring] = normalized.get(bitstring, 0) + int(value)
    return normalized


def run_qiskit_circuit_counts(qc, shots: int, backend: str = "auto", seed: int | None = 123) -> tuple[dict[str, int], str]:
    backend = backend.lower()

    if backend in {"auto", "aer"}:
        try:
            from qiskit_aer import AerSimulator
            sim = AerSimulator(seed_simulator=seed)
            result = sim.run(qc, shots=shots, seed_simulator=seed).result()
            return {str(k): int(v) for k, v in result.get_counts().items()}, "aer"
        except Exception:
            if backend == "aer":
                raise

    if backend in {"auto", "basic"}:
        try:
            from qiskit.providers.basic_provider import BasicSimulator
            sim = BasicSimulator()
            result = sim.run(qc, shots=shots, seed_simulator=seed).result()
            return {str(k): int(v) for k, v in result.get_counts().items()}, "basic"
        except Exception:
            if backend == "basic":
                raise

    raise RuntimeError("No Qiskit simulator backend was available.")


def hardware_dry_run_transpile_scaffold(qc, backend_name: str | None = None, optimization_level: int = 1) -> dict[str, Any]:
    """Dry-run-only scaffold. Does not call IBM Runtime or submit jobs."""
    try:
        depth = qc.depth()
        size = qc.size()
        width = qc.num_qubits
    except Exception:
        depth = None
        size = None
        width = None
    digest = hashlib.sha256(str(qc).encode("utf-8")).hexdigest()[:12]
    return {
        "dry_run_job_id": f"QISKIT-DRYRUN-{digest}",
        "backend_name": backend_name,
        "optimization_level": optimization_level,
        "depth": depth,
        "size": size,
        "width": width,
        "submitted": False,
        "message": "Hardware dry-run transpilation scaffold only. No IBM job submitted.",
    }


def term_expectations_from_counts(group: CommutingGroup, counts: dict[str, int]) -> dict[str, float]:
    out = {}
    for term in group.terms:
        out[term.normalized_string()] = expectation_from_counts_for_pauli(
            counts,
            term.normalized_string(),
            reverse_bitstrings=False,
        )
    return out


def execute_group_with_qiskit_or_fallback(
    component: PauliComponent,
    group: CommutingGroup,
    config: QiskitExecutionConfig,
    state_preparation_hook: Callable[[Any], Any] | None = None,
) -> QiskitGroupExecutionResult:
    spec, build_result, qc = build_circuit_or_fallback_spec(component, group, state_preparation_hook=state_preparation_hook)

    backend_choice = config.backend.lower()

    if backend_choice == "hardware_dry_run":
        if qc is not None:
            dry = hardware_dry_run_transpile_scaffold(
                qc,
                backend_name=config.hardware_backend_name,
                optimization_level=config.optimization_level,
            )
            counts = deterministic_counts_for_basis(component.name, group.measurement_basis, config.shots)
            term_exps = term_expectations_from_counts(group, counts)
            return QiskitGroupExecutionResult(
                component_name=component.name,
                group_id=group.group_id,
                measurement_basis=group.measurement_basis,
                backend_used="hardware_dry_run",
                status="dry_run_prepared",
                shots=config.shots,
                counts=counts,
                term_expectations=term_exps,
                circuit_build=build_result,
                job_id=dry["dry_run_job_id"],
                message=dry["message"],
                metadata=dry,
            )
        counts = deterministic_counts_for_basis(component.name, group.measurement_basis, config.shots)
        term_exps = term_expectations_from_counts(group, counts)
        return QiskitGroupExecutionResult(
            component_name=component.name,
            group_id=group.group_id,
            measurement_basis=group.measurement_basis,
            backend_used="hardware_dry_run_fallback",
            status="dry_run_prepared",
            shots=config.shots,
            counts=counts,
            term_expectations=term_exps,
            circuit_build=build_result,
            job_id="QISKIT-DRYRUN-FALLBACK",
            message="Hardware dry-run prepared using fallback counts. No IBM job submitted.",
        )

    if backend_choice != "fallback" and config.use_qiskit_if_available and qc is not None:
        try:
            raw_counts, backend_used = run_qiskit_circuit_counts(qc, config.shots, backend=backend_choice, seed=config.seed)
            counts = normalize_qiskit_counts(raw_counts, spec.n_qubits, reverse_bitstrings=config.reverse_bitstrings)
            term_exps = term_expectations_from_counts(group, counts)
            return QiskitGroupExecutionResult(
                component_name=component.name,
                group_id=group.group_id,
                measurement_basis=group.measurement_basis,
                backend_used=backend_used,
                status="completed",
                shots=config.shots,
                counts=counts,
                term_expectations=term_exps,
                circuit_build=build_result,
                message="Executed with Qiskit simulator backend.",
                metadata={"raw_counts": raw_counts},
            )
        except Exception as exc:
            if backend_choice in {"aer", "basic"}:
                raise
            # auto falls through to fallback.
            build_result.metadata["qiskit_execution_error"] = str(exc)

    counts = deterministic_counts_for_basis(component.name, group.measurement_basis, config.shots)
    term_exps = term_expectations_from_counts(group, counts)
    return QiskitGroupExecutionResult(
        component_name=component.name,
        group_id=group.group_id,
        measurement_basis=group.measurement_basis,
        backend_used="fallback",
        status="completed",
        shots=config.shots,
        counts=counts,
        term_expectations=term_exps,
        circuit_build=build_result,
        message="Executed with dependency-free fallback grouped-count simulator.",
    )


def execute_component_with_qiskit_or_fallback(
    component: PauliComponent,
    config: QiskitExecutionConfig,
    state_preparation_hook: Callable[[Any], Any] | None = None,
) -> QiskitComponentExecutionResult:
    compilation = compile_pauli_component(component, product_basis_only=True)
    group_results = [
        execute_group_with_qiskit_or_fallback(component, group, config, state_preparation_hook=state_preparation_hook)
        for group in compilation.groups
    ]
    grouped_measurement_results = [g.to_grouped_measurement_result() for g in group_results]
    estimate = reconstruct_component_estimate(component, grouped_measurement_results, config.shots)
    return QiskitComponentExecutionResult(
        component=component,
        compilation=compilation,
        group_results=group_results,
        component_estimate=estimate,
        metadata={"config": asdict(config)},
    )


def export_qiskit_group_results_json(component_results: list[QiskitComponentExecutionResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for component in component_results:
        payload.append({
            "component": asdict(component.component),
            "component_estimate": asdict(component.component_estimate),
            "groups": [asdict(g) for g in component.group_results],
        })
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
    return path


def export_qiskit_group_results_csv(component_results: list[QiskitComponentExecutionResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "component_name", "group_id", "measurement_basis", "backend_used",
            "status", "shots", "job_id", "counts_json", "term_expectations_json"
        ])
        for comp in component_results:
            for group in comp.group_results:
                writer.writerow([
                    group.component_name,
                    group.group_id,
                    group.measurement_basis,
                    group.backend_used,
                    group.status,
                    group.shots,
                    group.job_id,
                    json.dumps(group.counts),
                    json.dumps(group.term_expectations),
                ])
    return path


def export_circuit_builds_json(component_results: list[QiskitComponentExecutionResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    builds = []
    for comp in component_results:
        for group in comp.group_results:
            builds.append(asdict(group.circuit_build))
    path.write_text(json.dumps(builds, indent=2, default=_json_default), encoding="utf-8")
    return path


def make_qiskit_execution_report(result: ProductionQiskitExecutionResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.6 Qiskit Pauli Execution Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Execution config",
        "",
        "```text",
        result.config.summary(),
        "```",
        "",
        "## Component estimates",
        "",
    ]
    for item in result.component_estimates:
        lines.extend(["```text", item.summary(), "```", ""])
    lines.extend(["## Group execution results", ""])
    for comp in result.component_results:
        for group in comp.group_results:
            lines.extend(["```text", group.summary(), "```", ""])
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
        "v3.6 performs local Qiskit/fallback simulation or hardware dry-run scaffolding only. No IBM hardware jobs are submitted.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_production_qiskit_execution(
    spec_or_path,
    backend: str = "auto",
    max_components: int | None = None,
    shots: int | None = None,
    hardware_backend_name: str | None = None,
) -> ProductionQiskitExecutionResult:
    if isinstance(spec_or_path, (str, Path)):
        spec = load_production_spec(spec_or_path)
    else:
        spec = spec_or_path

    output_dir = Path(spec.output_dir)
    qiskit_dir = output_dir / "qiskit_pauli_execution"
    qiskit_dir.mkdir(parents=True, exist_ok=True)

    actual_shots = int(shots or spec.execution_policy.shots)
    config = QiskitExecutionConfig(
        backend=backend,
        shots=actual_shots,
        seed=123,
        optimization_level=spec.execution_policy.optimization_level,
        reverse_bitstrings=True,
        use_qiskit_if_available=True,
        hardware_backend_name=hardware_backend_name or spec.execution_policy.backend_name,
    )

    warnings = []
    components = load_selected_pauli_components(spec, max_components=max_components)
    if not components:
        warnings.append("No Pauli components selected. Check component_registry_path and observable selection.")

    component_results = [execute_component_with_qiskit_or_fallback(component, config) for component in components]
    estimates = [item.component_estimate for item in component_results]

    artifacts = {}
    artifacts["qiskit_group_results_json"] = str(export_qiskit_group_results_json(component_results, qiskit_dir / "qiskit_group_results.json"))
    artifacts["qiskit_group_results_csv"] = str(export_qiskit_group_results_csv(component_results, qiskit_dir / "qiskit_group_results.csv"))
    artifacts["circuit_builds_json"] = str(export_circuit_builds_json(component_results, qiskit_dir / "circuit_builds.json"))
    artifacts["grouped_counts_json"] = str(export_grouped_counts_json(estimates, qiskit_dir / "grouped_counts.json"))
    artifacts["grouped_counts_csv"] = str(export_grouped_counts_csv(estimates, qiskit_dir / "grouped_counts.csv"))
    artifacts["component_estimates_csv"] = str(export_component_estimates_csv(estimates, qiskit_dir / "component_estimates.csv"))
    artifacts.update(export_mv_estimate_tables(estimates, qiskit_dir))
    artifacts["component_estimates_figure"] = str(plot_component_estimates(estimates, qiskit_dir / "component_estimates.png"))
    artifacts["mv_estimate_report"] = str(make_mv_estimate_report(estimates, qiskit_dir / "mv_estimate_report.md"))

    db, records = attach_pauli_estimates_to_database(
        spec=spec,
        estimates=estimates,
        database_path=output_dir / "database" / "production_qiskit_pauli_runs.jsonl",
        artifact_paths={
            "component_estimates_csv": artifacts["component_estimates_csv"],
            "qiskit_group_results_json": artifacts["qiskit_group_results_json"],
            "circuit_builds_json": artifacts["circuit_builds_json"],
            "M_estimates_csv": artifacts["M_estimates_csv"],
            "V_estimates_csv": artifacts["V_estimates_csv"],
        },
    )
    artifacts["qiskit_execution_database_jsonl"] = str(db.path)
    artifacts["qiskit_execution_run_table_csv"] = str(export_run_table_csv(records, output_dir / "database" / "qiskit_execution_run_table.csv"))
    artifacts["qiskit_execution_dashboard_json"] = str(export_dashboard_json(records, output_dir / "database" / "qiskit_execution_dashboard.json"))
    artifacts["qiskit_execution_database_report"] = str(make_run_database_report(records, output_dir / "database" / "qiskit_execution_database_report.md"))

    dashboard = build_dashboard_package(output_dir / "dashboard_qiskit_pauli", database_path=db.path)
    artifacts["dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")
    artifacts["artifact_browser_html"] = dashboard.artifacts.get("artifact_browser_html", "")

    result = ProductionQiskitExecutionResult(
        spec=spec,
        config=config,
        components=components,
        component_results=component_results,
        component_estimates=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
    )

    artifacts["qiskit_execution_report"] = str(make_qiskit_execution_report(result, qiskit_dir / "qiskit_execution_report.md"))

    manifest_path = qiskit_dir / "production_qiskit_execution_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.6 Qiskit Pauli execution",
        "summary": result.summary(),
        "config": asdict(config),
        "warnings": warnings,
        "artifacts": artifacts,
        "qiskit_available": qiskit_is_available(),
        "component_estimates": [
            {
                "component_name": item.component_name,
                "quantity": item.quantity,
                "family": item.family,
                "indices": item.indices,
                "estimate": [item.estimate.real, item.estimate.imag],
                "n_terms": item.n_terms,
                "n_groups": item.n_groups,
            }
            for item in estimates
        ],
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["production_qiskit_execution_manifest"] = str(manifest_path)

    return ProductionQiskitExecutionResult(
        spec=spec,
        config=config,
        components=components,
        component_results=component_results,
        component_estimates=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
    )
