from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import itertools
import json
import math
import time
import hashlib

from .pauli_compiler import (
    PauliTerm,
    PauliComponent,
    pauli_component_from_dict,
)
from .production import (
    load_production_spec,
    select_components_from_registry,
    _read_component_registry,
)
from .production_pauli_execution import (
    ComponentEstimateResult,
    GroupedMeasurementResult,
    deterministic_counts_for_basis,
    reconstruct_component_estimate,
    export_component_estimates_csv,
    export_mv_estimate_tables,
    plot_component_estimates,
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
class StabilizerCodeSpec:
    name: str
    n_physical: int
    n_logical: int
    stabilizers: list[str]
    logical_x: list[str]
    logical_z: list[str]
    distance: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "StabilizerCodeSpec\n"
            f"  name: {self.name}\n"
            f"  n_physical: {self.n_physical}\n"
            f"  n_logical: {self.n_logical}\n"
            f"  distance: {self.distance}\n"
            f"  stabilizers: {self.stabilizers}\n"
            f"  logical_x: {self.logical_x}\n"
            f"  logical_z: {self.logical_z}"
        )


@dataclass
class LogicalPauliTerm:
    coefficient: complex
    logical_pauli_string: str
    physical_pauli_string: str
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "LogicalPauliTerm\n"
            f"  coeff: {self.coefficient}\n"
            f"  logical: {self.logical_pauli_string}\n"
            f"  physical: {self.physical_pauli_string}\n"
            f"  label: {self.label}"
        )


@dataclass
class LogicalPauliComponent:
    name: str
    quantity: str
    indices: list[int]
    code: StabilizerCodeSpec
    logical_terms: list[LogicalPauliTerm]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_physical_qubits(self) -> int:
        return self.code.n_physical * max(1, len(self.logical_terms[0].logical_pauli_string)) if self.logical_terms else 0

    def summary(self) -> str:
        return (
            "LogicalPauliComponent\n"
            f"  name: {self.name}\n"
            f"  quantity: {self.quantity}\n"
            f"  indices: {self.indices}\n"
            f"  code: {self.code.name}\n"
            f"  logical_terms: {len(self.logical_terms)}"
        )


@dataclass
class SyndromeMeasurementSpec:
    syndrome_id: str
    stabilizer: str
    ancilla_qubit: int
    data_qubits: list[int]
    circuit_type: str = "stabilizer_syndrome_scaffold"
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "SyndromeMeasurementSpec\n"
            f"  syndrome_id: {self.syndrome_id}\n"
            f"  stabilizer: {self.stabilizer}\n"
            f"  ancilla: {self.ancilla_qubit}\n"
            f"  data_qubits: {self.data_qubits}"
        )


@dataclass
class LogicalObservableEstimate:
    component_name: str
    quantity: str
    family: str | None
    indices: list[int]
    code_name: str
    logical_estimate: complex
    physical_estimate: complex
    syndrome_acceptance: float
    n_logical_terms: int
    n_syndromes: int
    shots: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "LogicalObservableEstimate\n"
            f"  component: {self.component_name}\n"
            f"  quantity: {self.quantity}\n"
            f"  family: {self.family}\n"
            f"  code: {self.code_name}\n"
            f"  logical_estimate: {self.logical_estimate.real:+.10f}{self.logical_estimate.imag:+.10f}j\n"
            f"  physical_estimate: {self.physical_estimate.real:+.10f}{self.physical_estimate.imag:+.10f}j\n"
            f"  syndrome_acceptance: {self.syndrome_acceptance:.6f}\n"
            f"  terms: {self.n_logical_terms}\n"
            f"  syndromes: {self.n_syndromes}"
        )


@dataclass
class ProductionQECResult:
    project_name: str
    code: StabilizerCodeSpec
    logical_components: list[LogicalPauliComponent]
    estimates: list[LogicalObservableEstimate]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        by_quantity = {}
        for estimate in self.estimates:
            by_quantity[estimate.quantity] = by_quantity.get(estimate.quantity, 0) + 1
        return (
            "ProductionQECResult\n"
            f"  project: {self.project_name}\n"
            f"  code: {self.code.name}\n"
            f"  logical_components: {len(self.logical_components)}\n"
            f"  estimates: {len(self.estimates)}\n"
            f"  by_quantity: {by_quantity}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def _json_default(obj):
    if isinstance(obj, complex):
        return [obj.real, obj.imag]
    return str(obj)


def normalize_pauli_string(pauli: str, n: int | None = None) -> str:
    s = str(pauli).upper().replace(" ", "")
    if any(ch not in "IXYZ" for ch in s):
        raise ValueError(f"Invalid Pauli string: {pauli}")
    if n is not None:
        if len(s) > n:
            raise ValueError(f"Pauli string length {len(s)} exceeds requested length {n}.")
        s = s + "I" * (n - len(s))
    return s


def default_repetition_code(distance: int = 3) -> StabilizerCodeSpec:
    if distance < 3 or distance % 2 == 0:
        raise ValueError("Use an odd repetition-code distance >= 3.")
    stabilizers = []
    for i in range(distance - 1):
        s = ["I"] * distance
        s[i] = "Z"
        s[i + 1] = "Z"
        stabilizers.append("".join(s))
    return StabilizerCodeSpec(
        name=f"repetition{distance}",
        n_physical=distance,
        n_logical=1,
        stabilizers=stabilizers,
        logical_x=["X" * distance],
        logical_z=["Z" + "I" * (distance - 1)],
        distance=distance,
        metadata={"code_family": "bit_flip_repetition", "scaffold": True},
    )


def default_five_qubit_code() -> StabilizerCodeSpec:
    return StabilizerCodeSpec(
        name="five_qubit_perfect_scaffold",
        n_physical=5,
        n_logical=1,
        stabilizers=["XZZXI", "IXZZX", "XIXZZ", "ZXIXZ"],
        logical_x=["XXXXX"],
        logical_z=["ZZZZZ"],
        distance=3,
        metadata={"code_family": "perfect_code", "scaffold": True},
    )


def get_code_by_name(name: str) -> StabilizerCodeSpec:
    key = str(name).lower().replace("-", "").replace("_", "")
    if key in {"repetition3", "bitflip3", "rep3"}:
        return default_repetition_code(3)
    if key in {"repetition5", "bitflip5", "rep5"}:
        return default_repetition_code(5)
    if key in {"fivequbit", "fivequbitperfect", "perfect5", "fivequbitperfectscaffold"}:
        return default_five_qubit_code()
    raise KeyError(f"Unknown code name: {name}")


def pauli_product_char(a: str, b: str) -> str:
    # Phase is intentionally ignored in this scaffold.
    if a == "I":
        return b
    if b == "I":
        return a
    if a == b:
        return "I"
    pairs = {frozenset(("X", "Z")): "Y", frozenset(("X", "Y")): "Z", frozenset(("Y", "Z")): "X"}
    return pairs[frozenset((a, b))]


def pauli_product_ignore_phase(a: str, b: str) -> str:
    a = normalize_pauli_string(a)
    b = normalize_pauli_string(b)
    if len(a) != len(b):
        raise ValueError("Pauli strings must have same length.")
    return "".join(pauli_product_char(x, y) for x, y in zip(a, b))


def map_single_logical_pauli_to_physical(ch: str, code: StabilizerCodeSpec, logical_index: int = 0) -> str:
    ch = ch.upper()
    if ch == "I":
        return "I" * code.n_physical
    if ch == "X":
        return code.logical_x[logical_index]
    if ch == "Z":
        return code.logical_z[logical_index]
    if ch == "Y":
        return pauli_product_ignore_phase(code.logical_x[logical_index], code.logical_z[logical_index])
    raise ValueError(f"Invalid logical Pauli character: {ch}")


def map_logical_pauli_string_to_physical(logical_pauli: str, code: StabilizerCodeSpec) -> str:
    logical_pauli = normalize_pauli_string(logical_pauli)
    physical_blocks = []
    for ch in logical_pauli:
        physical_blocks.append(map_single_logical_pauli_to_physical(ch, code, logical_index=0))
    return "".join(physical_blocks)


def map_pauli_term_to_logical(term: PauliTerm, code: StabilizerCodeSpec) -> LogicalPauliTerm:
    logical = term.normalized_string()
    physical = map_logical_pauli_string_to_physical(logical, code)
    return LogicalPauliTerm(
        coefficient=term.coefficient,
        logical_pauli_string=logical,
        physical_pauli_string=physical,
        label=term.label,
        metadata={**term.metadata, "source": "map_pauli_term_to_logical"},
    )


def map_component_to_logical(component: PauliComponent, code: StabilizerCodeSpec) -> LogicalPauliComponent:
    logical_terms = [map_pauli_term_to_logical(term, code) for term in component.terms]
    return LogicalPauliComponent(
        name=component.name,
        quantity=component.quantity,
        indices=list(component.indices),
        code=code,
        logical_terms=logical_terms,
        metadata={**component.metadata, "logical_mapping": code.name},
    )


def make_syndrome_specs(code: StabilizerCodeSpec, logical_block_index: int = 0) -> list[SyndromeMeasurementSpec]:
    offset = logical_block_index * code.n_physical
    specs = []
    for i, stabilizer in enumerate(code.stabilizers):
        specs.append(
            SyndromeMeasurementSpec(
                syndrome_id=f"{code.name}_s{i}",
                stabilizer=stabilizer,
                ancilla_qubit=offset + code.n_physical + i,
                data_qubits=list(range(offset, offset + code.n_physical)),
                metadata={"logical_block_index": logical_block_index},
            )
        )
    return specs


def syndrome_acceptance_probability(code: StabilizerCodeSpec, physical_error_rate: float = 0.01) -> float:
    n_checks = max(1, len(code.stabilizers))
    return float(max(0.0, min(1.0, (1.0 - physical_error_rate) ** n_checks)))


def _stable_unit_interval(text: str) -> float:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    intval = int(digest[:14], 16)
    return intval / float(16 ** 14 - 1)


def deterministic_logical_expectation(component_name: str, pauli: str, code: StabilizerCodeSpec) -> float:
    active = sum(1 for ch in pauli if ch != "I")
    unit = _stable_unit_interval(f"{component_name}|{pauli}|{code.name}|{active}")
    base = -0.8 + 1.6 * unit
    protection = 1.0 - 0.02 / max(1, code.distance or 1)
    return float(max(-1.0, min(1.0, base * protection)))


def estimate_logical_component(
    component: LogicalPauliComponent,
    shots: int = 1024,
    physical_error_rate: float = 0.01,
) -> LogicalObservableEstimate:
    logical_total = 0.0 + 0.0j
    physical_total = 0.0 + 0.0j

    acceptance = syndrome_acceptance_probability(component.code, physical_error_rate=physical_error_rate)
    grouped_results: list[GroupedMeasurementResult] = []

    for term in component.logical_terms:
        logical_exp = deterministic_logical_expectation(component.name, term.logical_pauli_string, component.code)
        physical_exp = deterministic_logical_expectation(component.name, term.physical_pauli_string, component.code) * acceptance

        logical_total += term.coefficient * logical_exp
        physical_total += term.coefficient * physical_exp

        basis = term.physical_pauli_string.replace("Y", "X")
        counts = deterministic_counts_for_basis(component.name, basis, shots)
        grouped_results.append(
            GroupedMeasurementResult(
                component_name=component.name,
                group_id=f"logical_{term.label or term.logical_pauli_string}",
                measurement_basis=basis,
                shots=shots,
                counts=counts,
                term_expectations={term.physical_pauli_string: physical_exp},
                metadata={
                    "logical_pauli_string": term.logical_pauli_string,
                    "physical_pauli_string": term.physical_pauli_string,
                    "syndrome_acceptance": acceptance,
                },
            )
        )

    family = component.metadata.get("component_family") if component.metadata else None
    return LogicalObservableEstimate(
        component_name=component.name,
        quantity=component.quantity,
        family=family,
        indices=list(component.indices),
        code_name=component.code.name,
        logical_estimate=logical_total,
        physical_estimate=physical_total,
        syndrome_acceptance=acceptance,
        n_logical_terms=len(component.logical_terms),
        n_syndromes=len(component.code.stabilizers),
        shots=shots,
        metadata={
            "physical_error_rate": physical_error_rate,
            "grouped_results": [asdict(x) for x in grouped_results],
        },
    )


def load_selected_components_for_qec(spec_or_path, max_components: int | None = None) -> list[PauliComponent]:
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    if not spec.component_registry_path:
        return []
    registry = _read_component_registry(spec.component_registry_path)
    selected = select_components_from_registry(registry, spec.observable_selection)
    if max_components is not None:
        selected = selected[:max_components]
    return [pauli_component_from_dict(x) for x in selected]


def export_logical_components_json(components: list[LogicalPauliComponent], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(c) for c in components], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_syndrome_specs_json(specs: list[SyndromeMeasurementSpec], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(s) for s in specs], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_logical_estimates_csv(estimates: list[LogicalObservableEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "component_name", "quantity", "family", "indices", "code_name",
            "logical_estimate_real", "logical_estimate_imag",
            "physical_estimate_real", "physical_estimate_imag",
            "syndrome_acceptance", "n_logical_terms", "n_syndromes", "shots"
        ])
        for e in estimates:
            writer.writerow([
                e.component_name,
                e.quantity,
                e.family,
                json.dumps(e.indices),
                e.code_name,
                e.logical_estimate.real,
                e.logical_estimate.imag,
                e.physical_estimate.real,
                e.physical_estimate.imag,
                e.syndrome_acceptance,
                e.n_logical_terms,
                e.n_syndromes,
                e.shots,
            ])
    return path


def export_logical_estimates_json(estimates: list[LogicalObservableEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(e) for e in estimates], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_qec_mv_tables(estimates: list[LogicalObservableEstimate], output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    m_path = output_dir / "M_logical_estimates.csv"
    v_path = output_dir / "V_logical_estimates.csv"
    for quantity, path in [("M", m_path), ("V", v_path)]:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "component_name", "family", "indices", "code_name",
                "logical_estimate_real", "logical_estimate_imag",
                "physical_estimate_real", "physical_estimate_imag",
                "syndrome_acceptance"
            ])
            for e in estimates:
                if e.quantity == quantity:
                    writer.writerow([
                        e.component_name,
                        e.family,
                        json.dumps(e.indices),
                        e.code_name,
                        e.logical_estimate.real,
                        e.logical_estimate.imag,
                        e.physical_estimate.real,
                        e.physical_estimate.imag,
                        e.syndrome_acceptance,
                    ])
    return {"M_logical_estimates_csv": str(m_path), "V_logical_estimates_csv": str(v_path)}


def plot_logical_estimates(estimates: list[LogicalObservableEstimate], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(e.summary() for e in estimates), encoding="utf-8")
        return txt

    labels = [e.component_name for e in estimates]
    logical = [e.logical_estimate.real for e in estimates]
    physical = [e.physical_estimate.real for e in estimates]
    x = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, logical, marker="o", label="logical")
    ax.plot(x, physical, marker="s", label="physical with syndrome acceptance")
    ax.set_xlabel("component")
    ax.set_ylabel("estimate real part")
    ax.set_title("QEC-aware logical vs physical estimates")
    if len(labels) <= 10:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def attach_qec_estimates_to_database(spec, estimates: list[LogicalObservableEstimate], database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    records = []
    for e in estimates:
        artifacts = [
            artifact_from_path(path, name=name, artifact_type="qec_logical_artifact")
            for name, path in artifact_paths.items()
        ]
        record = new_run_record(
            name=f"qec_{e.component_name}",
            run_type="qec_logical_estimate",
            status="completed",
            tags=["qec", "logical", e.family or "unknown", e.quantity],
            parameters={
                "component_name": e.component_name,
                "quantity": e.quantity,
                "indices": e.indices,
                "code_name": e.code_name,
                "n_logical_terms": e.n_logical_terms,
                "n_syndromes": e.n_syndromes,
                "shots": e.shots,
            },
            metrics={
                "logical_estimate_real": e.logical_estimate.real,
                "logical_estimate_imag": e.logical_estimate.imag,
                "physical_estimate_real": e.physical_estimate.real,
                "physical_estimate_imag": e.physical_estimate.imag,
                "syndrome_acceptance": e.syndrome_acceptance,
                "n_logical_terms": float(e.n_logical_terms),
                "n_syndromes": float(e.n_syndromes),
            },
            backend=BackendMetadataRecord(
                backend_name="local_qec_logical_estimator",
                job_status="LOCAL_COMPLETED",
                timestamp_unix=time.time(),
            ),
            artifacts=artifacts,
            notes="QEC-aware logical observable estimate scaffold.",
        )
        db.append(record)
        records.append(record)
    return db, records


def make_qec_report(result: ProductionQECResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.1 QEC/Logical-Qubit Estimator Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Code",
        "",
        "```text",
        result.code.summary(),
        "```",
        "",
        "## Logical estimates",
        "",
    ]
    for estimate in result.estimates:
        lines.extend(["```text", estimate.summary(), "```", ""])
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
        "v4.1 is an initial QEC/logical-qubit scaffold. Replace the deterministic logical estimator and simplified logical mapping with the exact code-specific logical circuits, syndrome processing, and decoder before using results as final QEC data.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_qec_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    code = default_repetition_code(3)
    component = PauliComponent(
        name="demo_qec_Mbb_00",
        quantity="M",
        indices=[0, 0],
        terms=[
            PauliTerm(0.5, "ZI", label="t0"),
            PauliTerm(-0.25, "IZ", label="t1"),
            PauliTerm(0.1, "XX", label="t2"),
        ],
        metadata={"component_family": "Mbb"},
    )
    logical_component = map_component_to_logical(component, code)
    estimates = [estimate_logical_component(logical_component, shots=256)]
    syndromes = make_syndrome_specs(code)

    artifacts = {}
    artifacts["logical_components_json"] = str(export_logical_components_json([logical_component], output_dir / "logical_components.json"))
    artifacts["syndrome_specs_json"] = str(export_syndrome_specs_json(syndromes, output_dir / "syndrome_specs.json"))
    artifacts["logical_estimates_csv"] = str(export_logical_estimates_csv(estimates, output_dir / "logical_estimates.csv"))
    artifacts["logical_estimates_json"] = str(export_logical_estimates_json(estimates, output_dir / "logical_estimates.json"))
    artifacts.update(export_qec_mv_tables(estimates, output_dir))
    artifacts["logical_estimates_figure"] = str(plot_logical_estimates(estimates, output_dir / "logical_estimates.png"))

    result = ProductionQECResult(
        project_name="qec_demo",
        code=code,
        logical_components=[logical_component],
        estimates=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )
    artifacts["qec_report"] = str(make_qec_report(result, output_dir / "qec_report.md"))

    manifest_path = output_dir / "qec_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.1 QEC/logical demo",
        "summary": result.summary(),
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionQECResult(
        project_name="qec_demo",
        code=code,
        logical_components=[logical_component],
        estimates=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )


def run_production_qec_estimator(
    spec_or_path,
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    physical_error_rate: float = 0.01,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir) / "qec_logical_estimator"
    output_dir.mkdir(parents=True, exist_ok=True)

    code = get_code_by_name(code_name)
    physical_components = load_selected_components_for_qec(spec, max_components=max_components)
    warnings = []
    if not physical_components:
        warnings.append("No components selected for QEC estimator. Check component_registry_path and observable selection.")

    logical_components = [map_component_to_logical(component, code) for component in physical_components]
    estimates = [
        estimate_logical_component(component, shots=shots, physical_error_rate=physical_error_rate)
        for component in logical_components
    ]

    # Syndrome specs for one logical block.
    syndromes = make_syndrome_specs(code)

    artifacts = {}
    artifacts["logical_components_json"] = str(export_logical_components_json(logical_components, output_dir / "logical_components.json"))
    artifacts["syndrome_specs_json"] = str(export_syndrome_specs_json(syndromes, output_dir / "syndrome_specs.json"))
    artifacts["logical_estimates_csv"] = str(export_logical_estimates_csv(estimates, output_dir / "logical_estimates.csv"))
    artifacts["logical_estimates_json"] = str(export_logical_estimates_json(estimates, output_dir / "logical_estimates.json"))
    artifacts.update(export_qec_mv_tables(estimates, output_dir))
    artifacts["logical_estimates_figure"] = str(plot_logical_estimates(estimates, output_dir / "logical_estimates.png"))

    db, records = attach_qec_estimates_to_database(
        spec=spec,
        estimates=estimates,
        database_path=Path(spec.output_dir) / "database" / "qec_logical_estimates.jsonl",
        artifact_paths={
            "logical_estimates_csv": artifacts["logical_estimates_csv"],
            "logical_components_json": artifacts["logical_components_json"],
            "syndrome_specs_json": artifacts["syndrome_specs_json"],
        },
    )
    artifacts["qec_database_jsonl"] = str(db.path)
    artifacts["qec_run_table_csv"] = str(export_run_table_csv(records, Path(spec.output_dir) / "database" / "qec_run_table.csv"))
    artifacts["qec_dashboard_json"] = str(export_dashboard_json(records, Path(spec.output_dir) / "database" / "qec_dashboard.json"))
    artifacts["qec_database_report"] = str(make_run_database_report(records, Path(spec.output_dir) / "database" / "qec_database_report.md"))

    dashboard = build_dashboard_package(Path(spec.output_dir) / "dashboard_qec_logical", database_path=db.path)
    artifacts["qec_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["qec_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")

    result = ProductionQECResult(
        project_name=spec.project_name,
        code=code,
        logical_components=logical_components,
        estimates=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"physical_error_rate": physical_error_rate},
    )
    artifacts["qec_report"] = str(make_qec_report(result, output_dir / "qec_logical_estimator_report.md"))

    manifest_path = output_dir / "production_qec_estimator_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.1 production QEC logical estimator",
        "project": spec.project_name,
        "summary": result.summary(),
        "code": asdict(code),
        "warnings": warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionQECResult(
        project_name=spec.project_name,
        code=code,
        logical_components=logical_components,
        estimates=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"physical_error_rate": physical_error_rate},
    )
