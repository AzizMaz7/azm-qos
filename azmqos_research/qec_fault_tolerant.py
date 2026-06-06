from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import math
import time

from .qec_logical import (
    StabilizerCodeSpec,
    get_code_by_name,
)
from .qec_decoder import (
    ProductionQECDecoderResult,
    DecodedLogicalEstimate,
    run_production_qec_decoder,
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
class CircuitNoiseModel:
    name: str = "phenomenological_scaffold"
    data_error_rate: float = 0.01
    measurement_error_rate: float = 0.02
    two_qubit_error_rate: float = 0.015
    idle_error_rate: float = 0.001
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "CircuitNoiseModel\n"
            f"  name: {self.name}\n"
            f"  data_error_rate: {self.data_error_rate}\n"
            f"  measurement_error_rate: {self.measurement_error_rate}\n"
            f"  two_qubit_error_rate: {self.two_qubit_error_rate}\n"
            f"  idle_error_rate: {self.idle_error_rate}"
        )


@dataclass
class SyndromeExtractionCircuitSpec:
    circuit_id: str
    code_name: str
    stabilizer_index: int
    stabilizer: str
    round_index: int
    data_qubits: list[int]
    ancilla_qubit: int
    operations: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "SyndromeExtractionCircuitSpec\n"
            f"  circuit_id: {self.circuit_id}\n"
            f"  code: {self.code_name}\n"
            f"  round: {self.round_index}\n"
            f"  stabilizer_index: {self.stabilizer_index}\n"
            f"  stabilizer: {self.stabilizer}\n"
            f"  ancilla: {self.ancilla_qubit}\n"
            f"  operations: {len(self.operations)}"
        )


@dataclass
class SyndromeRoundResult:
    component_name: str
    round_index: int
    syndrome: str
    detected: bool
    decoder_correction: str
    logical_failure: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "SyndromeRoundResult\n"
            f"  component: {self.component_name}\n"
            f"  round: {self.round_index}\n"
            f"  syndrome: {self.syndrome}\n"
            f"  detected: {self.detected}\n"
            f"  correction: {self.decoder_correction}\n"
            f"  logical_failure: {self.logical_failure}"
        )


@dataclass
class FaultTolerantComponentResult:
    component_name: str
    quantity: str
    family: str | None
    indices: list[int]
    code_name: str
    rounds: int
    shots: int
    raw_estimate: float
    decoded_estimate: float
    ft_corrected_estimate: float
    logical_failure_rate: float
    decoder_acceptance_rate: float
    uncertainty: float
    round_results: list[SyndromeRoundResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "FaultTolerantComponentResult\n"
            f"  component: {self.component_name}\n"
            f"  quantity: {self.quantity}\n"
            f"  code: {self.code_name}\n"
            f"  rounds: {self.rounds}\n"
            f"  raw_estimate: {self.raw_estimate:+.10f}\n"
            f"  decoded_estimate: {self.decoded_estimate:+.10f}\n"
            f"  ft_corrected_estimate: {self.ft_corrected_estimate:+.10f}\n"
            f"  logical_failure_rate: {self.logical_failure_rate:.8e}\n"
            f"  decoder_acceptance_rate: {self.decoder_acceptance_rate:.6f}\n"
            f"  uncertainty: {self.uncertainty:.8e}"
        )


@dataclass
class DecoderComparisonSummary:
    component_name: str
    raw_error: float
    decoded_error: float
    ft_error: float
    improvement_vs_raw: float
    improvement_vs_decoded: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "DecoderComparisonSummary\n"
            f"  component: {self.component_name}\n"
            f"  raw_error: {self.raw_error:.8e}\n"
            f"  decoded_error: {self.decoded_error:.8e}\n"
            f"  ft_error: {self.ft_error:.8e}\n"
            f"  improvement_vs_raw: {self.improvement_vs_raw:.6f}\n"
            f"  improvement_vs_decoded: {self.improvement_vs_decoded:.6f}"
        )


@dataclass
class ProductionFTQECResult:
    project_name: str
    code: StabilizerCodeSpec
    noise_model: CircuitNoiseModel
    component_results: list[FaultTolerantComponentResult]
    decoder_comparisons: list[DecoderComparisonSummary]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        by_quantity = {}
        for item in self.component_results:
            by_quantity[item.quantity] = by_quantity.get(item.quantity, 0) + 1
        return (
            "ProductionFTQECResult\n"
            f"  project: {self.project_name}\n"
            f"  code: {self.code.name}\n"
            f"  components: {len(self.component_results)}\n"
            f"  comparisons: {len(self.decoder_comparisons)}\n"
            f"  by_quantity: {by_quantity}\n"
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


def make_syndrome_extraction_circuit_spec(
    code: StabilizerCodeSpec,
    stabilizer_index: int,
    round_index: int,
    data_offset: int = 0,
) -> SyndromeExtractionCircuitSpec:
    stabilizer = code.stabilizers[stabilizer_index]
    data_qubits = list(range(data_offset, data_offset + code.n_physical))
    ancilla = data_offset + code.n_physical + stabilizer_index

    ops = [{"gate": "reset", "qubits": [ancilla], "label": "reset_ancilla"}]
    for q, p in zip(data_qubits, stabilizer):
        if p == "I":
            continue
        if p == "X":
            ops.append({"gate": "H", "qubits": [q], "label": "basis_X"})
            ops.append({"gate": "CX", "qubits": [q, ancilla], "label": "stabilizer_coupling_X"})
            ops.append({"gate": "H", "qubits": [q], "label": "undo_basis_X"})
        elif p == "Y":
            ops.append({"gate": "Sdg", "qubits": [q], "label": "basis_Y_sdg"})
            ops.append({"gate": "H", "qubits": [q], "label": "basis_Y_h"})
            ops.append({"gate": "CX", "qubits": [q, ancilla], "label": "stabilizer_coupling_Y"})
            ops.append({"gate": "H", "qubits": [q], "label": "undo_basis_Y_h"})
            ops.append({"gate": "S", "qubits": [q], "label": "undo_basis_Y_s"})
        elif p == "Z":
            ops.append({"gate": "CX", "qubits": [q, ancilla], "label": "stabilizer_coupling_Z"})
        else:
            raise ValueError(f"Invalid stabilizer character: {p}")
    ops.append({"gate": "measure", "qubits": [ancilla], "label": f"syndrome_s{stabilizer_index}_r{round_index}"})

    return SyndromeExtractionCircuitSpec(
        circuit_id=f"{code.name}_s{stabilizer_index}_r{round_index}",
        code_name=code.name,
        stabilizer_index=stabilizer_index,
        stabilizer=stabilizer,
        round_index=round_index,
        data_qubits=data_qubits,
        ancilla_qubit=ancilla,
        operations=ops,
        metadata={"data_offset": data_offset},
    )


def make_repeated_syndrome_schedule(
    code: StabilizerCodeSpec,
    rounds: int = 3,
) -> list[SyndromeExtractionCircuitSpec]:
    specs = []
    for r in range(rounds):
        for s in range(len(code.stabilizers)):
            specs.append(make_syndrome_extraction_circuit_spec(code, s, r))
    return specs


def syndrome_spec_to_qiskit(spec: SyndromeExtractionCircuitSpec):
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:
        raise ImportError("Qiskit is not installed. Install with: python -m pip install qiskit") from exc

    n_qubits = max([spec.ancilla_qubit] + spec.data_qubits) + 1
    qc = QuantumCircuit(n_qubits, 1)
    for op in spec.operations:
        gate = op["gate"]
        qs = op["qubits"]
        if gate == "reset":
            qc.reset(qs[0])
        elif gate == "H":
            qc.h(qs[0])
        elif gate == "Sdg":
            qc.sdg(qs[0])
        elif gate == "S":
            qc.s(qs[0])
        elif gate == "CX":
            qc.cx(qs[0], qs[1])
        elif gate == "measure":
            qc.measure(qs[0], 0)
        else:
            raise ValueError(f"Unsupported gate in syndrome spec: {gate}")
    return qc


def effective_round_error_probability(noise: CircuitNoiseModel, code: StabilizerCodeSpec) -> float:
    checks = max(1, len(code.stabilizers))
    p = (
        noise.measurement_error_rate
        + 0.5 * noise.data_error_rate
        + 0.25 * noise.two_qubit_error_rate * checks
        + noise.idle_error_rate
    )
    return float(max(0.0, min(1.0, p)))


def simulate_repeated_syndrome_rounds(
    component_name: str,
    code: StabilizerCodeSpec,
    rounds: int,
    noise: CircuitNoiseModel,
) -> list[SyndromeRoundResult]:
    p_round = effective_round_error_probability(noise, code)
    results = []
    for r in range(rounds):
        u = _stable_unit_interval(f"{component_name}|{code.name}|round|{r}|{noise.name}")
        detected = u < p_round
        if not detected:
            syndrome = "0" * len(code.stabilizers)
            correction = "none"
            failure = False
        else:
            # Deterministic nonzero syndrome and correction scaffold.
            index = min(len(code.stabilizers) - 1, int(_stable_unit_interval(f"{component_name}|syndrome|{r}") * len(code.stabilizers)))
            bits = ["0"] * len(code.stabilizers)
            bits[index] = "1"
            syndrome = "".join(bits)
            correction = f"lookup_s{index}"
            fail_u = _stable_unit_interval(f"{component_name}|logical_failure|{r}|{noise.name}")
            failure = fail_u < (p_round / max(1, code.distance or 1))
        results.append(
            SyndromeRoundResult(
                component_name=component_name,
                round_index=r,
                syndrome=syndrome,
                detected=detected,
                decoder_correction=correction,
                logical_failure=failure,
                metadata={"p_round": p_round},
            )
        )
    return results


def estimate_logical_failure_rate(
    component_name: str,
    code: StabilizerCodeSpec,
    rounds: int,
    noise: CircuitNoiseModel,
    shots: int,
) -> float:
    # Scaffold: combine deterministic per-shot variation with round simulation.
    failures = 0
    for shot in range(shots):
        shot_noise = CircuitNoiseModel(
            name=f"{noise.name}_shot{shot}",
            data_error_rate=noise.data_error_rate,
            measurement_error_rate=noise.measurement_error_rate,
            two_qubit_error_rate=noise.two_qubit_error_rate,
            idle_error_rate=noise.idle_error_rate,
        )
        rounds_result = simulate_repeated_syndrome_rounds(f"{component_name}_shot{shot}", code, rounds, shot_noise)
        if any(r.logical_failure for r in rounds_result):
            failures += 1
    return failures / max(1, shots)


def ft_correct_decoded_estimate(
    decoded: DecodedLogicalEstimate,
    code: StabilizerCodeSpec,
    rounds: int,
    noise: CircuitNoiseModel,
) -> FaultTolerantComponentResult:
    round_results = simulate_repeated_syndrome_rounds(decoded.component_name, code, rounds, noise)
    failure_rate = estimate_logical_failure_rate(decoded.component_name, code, rounds, noise, decoded.shots)
    acceptance = sum(1 for r in round_results if not r.detected) / max(1, len(round_results))

    # Simple scaffold: FT correction damps the decoded estimate by logical failure probability.
    ft_estimate = decoded.corrected_estimate * (1.0 - 2.0 * failure_rate)
    uncertainty = math.sqrt(max(0.0, failure_rate * (1.0 - failure_rate)) / max(1, decoded.shots))
    uncertainty = math.sqrt(uncertainty * uncertainty + decoded.uncertainty * decoded.uncertainty)

    return FaultTolerantComponentResult(
        component_name=decoded.component_name,
        quantity=decoded.quantity,
        family=decoded.family,
        indices=list(decoded.indices),
        code_name=decoded.code_name,
        rounds=rounds,
        shots=decoded.shots,
        raw_estimate=decoded.raw_estimate,
        decoded_estimate=decoded.corrected_estimate,
        ft_corrected_estimate=ft_estimate,
        logical_failure_rate=failure_rate,
        decoder_acceptance_rate=acceptance,
        uncertainty=uncertainty,
        round_results=round_results,
        metadata={
            "postselected_estimate": decoded.postselected_estimate,
            "noise_model": asdict(noise),
        },
    )


def make_decoder_comparison(component: FaultTolerantComponentResult) -> DecoderComparisonSummary:
    reference = component.ft_corrected_estimate
    raw_error = abs(component.raw_estimate - reference)
    decoded_error = abs(component.decoded_estimate - reference)
    ft_error = component.uncertainty
    improvement_vs_raw = raw_error / max(ft_error, 1e-12)
    improvement_vs_decoded = decoded_error / max(ft_error, 1e-12)
    return DecoderComparisonSummary(
        component_name=component.component_name,
        raw_error=raw_error,
        decoded_error=decoded_error,
        ft_error=ft_error,
        improvement_vs_raw=improvement_vs_raw,
        improvement_vs_decoded=improvement_vs_decoded,
    )


def export_syndrome_circuit_specs_json(specs: list[SyndromeExtractionCircuitSpec], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(s) for s in specs], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_ft_component_results_csv(results: list[FaultTolerantComponentResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "component_name", "quantity", "family", "indices", "code_name", "rounds", "shots",
            "raw_estimate", "decoded_estimate", "ft_corrected_estimate",
            "logical_failure_rate", "decoder_acceptance_rate", "uncertainty"
        ])
        for r in results:
            writer.writerow([
                r.component_name, r.quantity, r.family, json.dumps(r.indices), r.code_name, r.rounds, r.shots,
                r.raw_estimate, r.decoded_estimate, r.ft_corrected_estimate,
                r.logical_failure_rate, r.decoder_acceptance_rate, r.uncertainty,
            ])
    return path


def export_ft_component_results_json(results: list[FaultTolerantComponentResult], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(r) for r in results], indent=2, default=_json_default), encoding="utf-8")
    return path


def export_decoder_comparisons_csv(comparisons: list[DecoderComparisonSummary], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["component_name", "raw_error", "decoded_error", "ft_error", "improvement_vs_raw", "improvement_vs_decoded"])
        for c in comparisons:
            writer.writerow([c.component_name, c.raw_error, c.decoded_error, c.ft_error, c.improvement_vs_raw, c.improvement_vs_decoded])
    return path


def export_ft_mv_tables(results: list[FaultTolerantComponentResult], output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    m_path = output_dir / "M_ft_qec_estimates.csv"
    v_path = output_dir / "V_ft_qec_estimates.csv"
    for quantity, path in [("M", m_path), ("V", v_path)]:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "component_name", "family", "indices", "code_name", "rounds",
                "ft_corrected_estimate", "logical_failure_rate", "decoder_acceptance_rate", "uncertainty"
            ])
            for r in results:
                if r.quantity == quantity:
                    writer.writerow([
                        r.component_name, r.family, json.dumps(r.indices), r.code_name, r.rounds,
                        r.ft_corrected_estimate, r.logical_failure_rate, r.decoder_acceptance_rate, r.uncertainty,
                    ])
    return {"M_ft_qec_estimates_csv": str(m_path), "V_ft_qec_estimates_csv": str(v_path)}


def plot_ft_qec_results(results: list[FaultTolerantComponentResult], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(r.summary() for r in results), encoding="utf-8")
        return txt

    labels = [r.component_name for r in results]
    raw = [r.raw_estimate for r in results]
    dec = [r.decoded_estimate for r in results]
    ft = [r.ft_corrected_estimate for r in results]
    x = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, raw, marker="o", label="raw")
    ax.plot(x, dec, marker="s", label="decoded")
    ax.plot(x, ft, marker="^", label="FT-corrected")
    ax.set_xlabel("component")
    ax.set_ylabel("estimate")
    ax.set_title("Fault-tolerant QEC estimates")
    if len(labels) <= 10:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def attach_ft_qec_to_database(spec, results: list[FaultTolerantComponentResult], database_path, artifact_paths: dict[str, str] | None = None):
    database_path = Path(database_path)
    db = ExperimentDatabase(database_path)
    artifact_paths = artifact_paths or {}
    records = []
    for r in results:
        artifacts = [
            artifact_from_path(path, name=name, artifact_type="ft_qec_artifact")
            for name, path in artifact_paths.items()
        ]
        record = new_run_record(
            name=f"ft_qec_{r.component_name}",
            run_type="fault_tolerant_qec_estimate",
            status="completed",
            tags=["qec", "fault_tolerant", r.family or "unknown", r.quantity],
            parameters={
                "component_name": r.component_name,
                "quantity": r.quantity,
                "indices": r.indices,
                "code_name": r.code_name,
                "rounds": r.rounds,
                "shots": r.shots,
            },
            metrics={
                "raw_estimate": r.raw_estimate,
                "decoded_estimate": r.decoded_estimate,
                "ft_corrected_estimate": r.ft_corrected_estimate,
                "logical_failure_rate": r.logical_failure_rate,
                "decoder_acceptance_rate": r.decoder_acceptance_rate,
                "uncertainty": r.uncertainty,
            },
            backend=BackendMetadataRecord(
                backend_name="local_ft_qec_simulator",
                job_status="LOCAL_COMPLETED",
                timestamp_unix=time.time(),
            ),
            artifacts=artifacts,
            notes="Fault-tolerant QEC syndrome-round scaffold estimate.",
        )
        db.append(record)
        records.append(record)
    return db, records


def make_ft_qec_report(result: ProductionFTQECResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v4.3 Fault-Tolerant QEC Report",
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
        "## Noise model",
        "",
        "```text",
        result.noise_model.summary(),
        "```",
        "",
        "## Component results",
        "",
    ]
    for item in result.component_results:
        lines.extend(["```text", item.summary(), "```", ""])
    lines.extend(["## Decoder comparisons", ""])
    for item in result.decoder_comparisons:
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
        "v4.3 is a fault-tolerant QEC scaffold. Replace deterministic syndrome/noise models with validated circuit-level simulations, repeated syndrome extraction circuits, and backend-specific noise before using results as final hardware QEC evidence.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_ft_qec_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    code = get_code_by_name("repetition3")
    noise = CircuitNoiseModel(data_error_rate=0.02, measurement_error_rate=0.03)
    schedule = make_repeated_syndrome_schedule(code, rounds=3)

    # Use v4.2 demo decoded estimates as base.
    from .qec_decoder import run_qec_decoder_demo
    decoded_demo = run_qec_decoder_demo(output_dir / "base_decoder_demo")
    component_results = [
        ft_correct_decoded_estimate(e, code=code, rounds=3, noise=noise)
        for e in decoded_demo.decoded_estimates
    ]
    comparisons = [make_decoder_comparison(r) for r in component_results]

    artifacts = {}
    artifacts["syndrome_circuit_specs_json"] = str(export_syndrome_circuit_specs_json(schedule, output_dir / "syndrome_circuit_specs.json"))
    artifacts["ft_component_results_csv"] = str(export_ft_component_results_csv(component_results, output_dir / "ft_component_results.csv"))
    artifacts["ft_component_results_json"] = str(export_ft_component_results_json(component_results, output_dir / "ft_component_results.json"))
    artifacts["decoder_comparisons_csv"] = str(export_decoder_comparisons_csv(comparisons, output_dir / "decoder_comparisons.csv"))
    artifacts.update(export_ft_mv_tables(component_results, output_dir))
    artifacts["ft_qec_figure"] = str(plot_ft_qec_results(component_results, output_dir / "ft_qec_results.png"))

    result = ProductionFTQECResult(
        project_name="ft_qec_demo",
        code=code,
        noise_model=noise,
        component_results=component_results,
        decoder_comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )
    artifacts["ft_qec_report"] = str(make_ft_qec_report(result, output_dir / "ft_qec_report.md"))

    manifest_path = output_dir / "ft_qec_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.3 FT-QEC demo",
        "summary": result.summary(),
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionFTQECResult(
        project_name="ft_qec_demo",
        code=code,
        noise_model=noise,
        component_results=component_results,
        decoder_comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )


def run_production_ft_qec(
    spec_or_path,
    code_name: str = "repetition3",
    max_components: int | None = None,
    shots: int = 1024,
    rounds: int = 3,
    physical_error_rate: float = 0.01,
    measurement_error_rate: float = 0.02,
):
    spec = load_production_spec(spec_or_path) if isinstance(spec_or_path, (str, Path)) else spec_or_path
    output_dir = Path(spec.output_dir) / "ft_qec"
    output_dir.mkdir(parents=True, exist_ok=True)

    code = get_code_by_name(code_name)
    noise = CircuitNoiseModel(
        data_error_rate=physical_error_rate,
        measurement_error_rate=measurement_error_rate,
        two_qubit_error_rate=max(physical_error_rate, measurement_error_rate) * 0.75,
        idle_error_rate=physical_error_rate * 0.1,
    )
    schedule = make_repeated_syndrome_schedule(code, rounds=rounds)

    decoded = run_production_qec_decoder(
        spec,
        code_name=code_name,
        max_components=max_components,
        shots=shots,
        physical_error_rate=physical_error_rate,
    )

    component_results = [
        ft_correct_decoded_estimate(e, code=code, rounds=rounds, noise=noise)
        for e in decoded.decoded_estimates
    ]
    comparisons = [make_decoder_comparison(r) for r in component_results]

    artifacts = {}
    artifacts["syndrome_circuit_specs_json"] = str(export_syndrome_circuit_specs_json(schedule, output_dir / "syndrome_circuit_specs.json"))
    artifacts["ft_component_results_csv"] = str(export_ft_component_results_csv(component_results, output_dir / "ft_component_results.csv"))
    artifacts["ft_component_results_json"] = str(export_ft_component_results_json(component_results, output_dir / "ft_component_results.json"))
    artifacts["decoder_comparisons_csv"] = str(export_decoder_comparisons_csv(comparisons, output_dir / "decoder_comparisons.csv"))
    artifacts.update(export_ft_mv_tables(component_results, output_dir))
    artifacts["ft_qec_figure"] = str(plot_ft_qec_results(component_results, output_dir / "ft_qec_results.png"))

    db, records = attach_ft_qec_to_database(
        spec=spec,
        results=component_results,
        database_path=Path(spec.output_dir) / "database" / "ft_qec_estimates.jsonl",
        artifact_paths={
            "ft_component_results_csv": artifacts["ft_component_results_csv"],
            "syndrome_circuit_specs_json": artifacts["syndrome_circuit_specs_json"],
            "decoder_comparisons_csv": artifacts["decoder_comparisons_csv"],
        },
    )
    artifacts["ft_qec_database_jsonl"] = str(db.path)
    artifacts["ft_qec_run_table_csv"] = str(export_run_table_csv(records, Path(spec.output_dir) / "database" / "ft_qec_run_table.csv"))
    artifacts["ft_qec_dashboard_json"] = str(export_dashboard_json(records, Path(spec.output_dir) / "database" / "ft_qec_dashboard.json"))
    artifacts["ft_qec_database_report"] = str(make_run_database_report(records, Path(spec.output_dir) / "database" / "ft_qec_database_report.md"))

    dashboard = build_dashboard_package(Path(spec.output_dir) / "dashboard_ft_qec", database_path=db.path)
    artifacts["ft_qec_dashboard_manifest"] = dashboard.artifacts.get("manifest", "")
    artifacts["ft_qec_dashboard_html"] = dashboard.artifacts.get("dashboard_html", "")

    result = ProductionFTQECResult(
        project_name=spec.project_name,
        code=code,
        noise_model=noise,
        component_results=component_results,
        decoder_comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(decoded.warnings),
        metadata={
            "base_decoder_artifacts": decoded.artifacts,
            "rounds": rounds,
            "physical_error_rate": physical_error_rate,
            "measurement_error_rate": measurement_error_rate,
        },
    )
    artifacts["ft_qec_report"] = str(make_ft_qec_report(result, output_dir / "ft_qec_report.md"))

    manifest_path = output_dir / "production_ft_qec_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v4.3 production FT-QEC",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": result.warnings,
        "artifacts": artifacts,
    }, indent=2, default=_json_default), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionFTQECResult(
        project_name=spec.project_name,
        code=code,
        noise_model=noise,
        component_results=component_results,
        decoder_comparisons=comparisons,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(decoded.warnings),
        metadata={
            "base_decoder_artifacts": decoded.artifacts,
            "rounds": rounds,
            "physical_error_rate": physical_error_rate,
            "measurement_error_rate": measurement_error_rate,
        },
    )
