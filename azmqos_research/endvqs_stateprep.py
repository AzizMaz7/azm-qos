from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import json
import math
import time

from .pauli_compiler import PauliComponent, PauliTerm
from .production import load_production_spec
from .production_pauli_execution import load_selected_pauli_components
from .qiskit_pauli_execution import (
    QiskitExecutionConfig,
    execute_component_with_qiskit_or_fallback,
)


@dataclass
class ElectronicStateParameters:
    alpha: list[float] = field(default_factory=lambda: [0.10, -0.20])
    beta: list[float] = field(default_factory=lambda: [0.05, 0.12])
    entangler_strength: float = 0.15

    def summary(self) -> str:
        return (
            "ElectronicStateParameters\n"
            f"  alpha: {self.alpha}\n"
            f"  beta: {self.beta}\n"
            f"  entangler_strength: {self.entangler_strength}"
        )


@dataclass
class NuclearCoherentParameters:
    p: list[float] = field(default_factory=lambda: [0.20, -0.10])
    q: list[float] = field(default_factory=lambda: [0.15, 0.25])
    scale: float = 1.0

    def summary(self) -> str:
        return (
            "NuclearCoherentParameters\n"
            f"  p: {self.p}\n"
            f"  q: {self.q}\n"
            f"  scale: {self.scale}"
        )


@dataclass
class ENDVQSLayout:
    n_electronic_qubits: int = 2
    n_nuclear_qubits: int = 2
    n_ancilla_qubits: int = 0

    @property
    def n_system_qubits(self) -> int:
        return self.n_electronic_qubits + self.n_nuclear_qubits

    @property
    def n_total_qubits(self) -> int:
        return self.n_system_qubits + self.n_ancilla_qubits

    def summary(self) -> str:
        return (
            "ENDVQSLayout\n"
            f"  n_electronic_qubits: {self.n_electronic_qubits}\n"
            f"  n_nuclear_qubits: {self.n_nuclear_qubits}\n"
            f"  n_ancilla_qubits: {self.n_ancilla_qubits}\n"
            f"  n_total_qubits: {self.n_total_qubits}"
        )


@dataclass
class ENDVQSStatePreparationConfig:
    electronic: ElectronicStateParameters = field(default_factory=ElectronicStateParameters)
    nuclear: NuclearCoherentParameters = field(default_factory=NuclearCoherentParameters)
    layout: ENDVQSLayout = field(default_factory=ENDVQSLayout)
    derivative: str | None = None
    derivative_index: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ENDVQSStatePreparationConfig\n"
            f"{self.electronic.summary()}\n"
            f"{self.nuclear.summary()}\n"
            f"{self.layout.summary()}\n"
            f"  derivative: {self.derivative}\n"
            f"  derivative_index: {self.derivative_index}"
        )


@dataclass
class StatePreparationOperation:
    gate: str
    qubits: list[int]
    parameter: float | None = None
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return f"{self.gate}({self.qubits}, parameter={self.parameter}, label={self.label})"


@dataclass
class StatePreparationPlan:
    config: ENDVQSStatePreparationConfig
    operations: list[StatePreparationOperation]
    component_name: str | None = None
    quantity: str | None = None
    family: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "StatePreparationPlan\n"
            f"  component_name: {self.component_name}\n"
            f"  quantity: {self.quantity}\n"
            f"  family: {self.family}\n"
            f"  operations: {len(self.operations)}\n"
            f"  derivative: {self.config.derivative}\n"
            f"  derivative_index: {self.config.derivative_index}"
        )


@dataclass
class ENDVQSExecutionResult:
    component_name: str
    stateprep_plan: StatePreparationPlan
    component_execution_summary: str
    estimate_real: float
    estimate_imag: float
    backend_used: str
    artifacts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ENDVQSExecutionResult\n"
            f"  component_name: {self.component_name}\n"
            f"  estimate: {self.estimate_real:+.10f}{self.estimate_imag:+.10f}j\n"
            f"  backend_used: {self.backend_used}\n"
            f"  operations: {len(self.stateprep_plan.operations)}"
        )


def electronic_params_from_dict(data: dict[str, Any] | None) -> ElectronicStateParameters:
    return ElectronicStateParameters(**(data or {}))


def nuclear_params_from_dict(data: dict[str, Any] | None) -> NuclearCoherentParameters:
    return NuclearCoherentParameters(**(data or {}))


def layout_from_dict(data: dict[str, Any] | None) -> ENDVQSLayout:
    return ENDVQSLayout(**(data or {}))


def stateprep_config_from_dict(data: dict[str, Any]) -> ENDVQSStatePreparationConfig:
    return ENDVQSStatePreparationConfig(
        electronic=electronic_params_from_dict(data.get("electronic")),
        nuclear=nuclear_params_from_dict(data.get("nuclear")),
        layout=layout_from_dict(data.get("layout")),
        derivative=data.get("derivative"),
        derivative_index=data.get("derivative_index"),
        metadata=dict(data.get("metadata", {})),
    )


def load_stateprep_config(path) -> ENDVQSStatePreparationConfig:
    path = Path(path)
    return stateprep_config_from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_stateprep_config(config: ENDVQSStatePreparationConfig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2, default=str), encoding="utf-8")
    return path


def make_fukutome_electronic_operations(params: ElectronicStateParameters, layout: ENDVQSLayout) -> list[StatePreparationOperation]:
    ops: list[StatePreparationOperation] = []
    n = layout.n_electronic_qubits
    for i in range(n):
        alpha = params.alpha[i % len(params.alpha)]
        beta = params.beta[i % len(params.beta)]
        ops.append(StatePreparationOperation("RY", [i], 2.0 * alpha, label=f"fukutome_alpha_{i}"))
        ops.append(StatePreparationOperation("RZ", [i], 2.0 * beta, label=f"fukutome_beta_{i}"))
    for i in range(max(0, n - 1)):
        ops.append(StatePreparationOperation("CX", [i, i + 1], None, label=f"electronic_entangler_{i}_{i+1}"))
        ops.append(StatePreparationOperation("RZ", [i + 1], params.entangler_strength, label=f"electronic_entangler_phase_{i}_{i+1}"))
        ops.append(StatePreparationOperation("CX", [i, i + 1], None, label=f"electronic_uncompute_entangler_{i}_{i+1}"))
    return ops


def make_nuclear_coherent_operations(params: NuclearCoherentParameters, layout: ENDVQSLayout) -> list[StatePreparationOperation]:
    ops: list[StatePreparationOperation] = []
    offset = layout.n_electronic_qubits
    n = layout.n_nuclear_qubits
    for j in range(n):
        p = params.p[j % len(params.p)] * params.scale
        q = params.q[j % len(params.q)] * params.scale
        qubit = offset + j
        ops.append(StatePreparationOperation("RY", [qubit], 2.0 * p, label=f"coherent_p_{j}"))
        ops.append(StatePreparationOperation("RZ", [qubit], 2.0 * q, label=f"coherent_q_{j}"))
    return ops


def derivative_operations(config: ENDVQSStatePreparationConfig) -> list[StatePreparationOperation]:
    if config.derivative is None:
        return []

    idx = int(config.derivative_index or 0)
    derivative = str(config.derivative).lower()

    if derivative in {"alpha", "beta"}:
        qubit = idx % max(1, config.layout.n_electronic_qubits)
    elif derivative in {"p", "q"}:
        qubit = config.layout.n_electronic_qubits + (idx % max(1, config.layout.n_nuclear_qubits))
    else:
        qubit = idx % max(1, config.layout.n_system_qubits)

    if derivative in {"alpha", "p"}:
        return [StatePreparationOperation("RX", [qubit], math.pi / 2.0, label=f"derivative_{derivative}_{idx}")]
    if derivative in {"beta", "q"}:
        return [StatePreparationOperation("RZ", [qubit], math.pi / 2.0, label=f"derivative_{derivative}_{idx}")]
    return [StatePreparationOperation("H", [qubit], None, label=f"derivative_generic_{derivative}_{idx}")]


def make_endvqs_stateprep_plan(
    config: ENDVQSStatePreparationConfig,
    component: PauliComponent | None = None,
) -> StatePreparationPlan:
    ops = []
    ops.extend(make_fukutome_electronic_operations(config.electronic, config.layout))
    ops.extend(make_nuclear_coherent_operations(config.nuclear, config.layout))
    ops.extend(derivative_operations(config))

    family = component.metadata.get("component_family") if component and component.metadata else None
    return StatePreparationPlan(
        config=config,
        operations=ops,
        component_name=component.name if component else None,
        quantity=component.quantity if component else None,
        family=family,
        metadata={"created_at_unix": time.time(), "n_operations": len(ops)},
    )


def apply_stateprep_operations_to_qiskit(qc, operations: list[StatePreparationOperation]):
    for op in operations:
        gate = op.gate.upper()
        qs = op.qubits
        if gate == "RY":
            qc.ry(float(op.parameter), qs[0])
        elif gate == "RZ":
            qc.rz(float(op.parameter), qs[0])
        elif gate == "RX":
            qc.rx(float(op.parameter), qs[0])
        elif gate == "H":
            qc.h(qs[0])
        elif gate == "X":
            qc.x(qs[0])
        elif gate == "CX":
            qc.cx(qs[0], qs[1])
        elif gate == "CZ":
            qc.cz(qs[0], qs[1])
        else:
            raise ValueError(f"Unsupported state-preparation gate: {op.gate}")
    return qc


def make_qiskit_stateprep_hook(plan: StatePreparationPlan):
    def hook(qc):
        valid_ops = []
        n = getattr(qc, "num_qubits", 0)
        for op in plan.operations:
            if all(q < n for q in op.qubits):
                valid_ops.append(op)
        return apply_stateprep_operations_to_qiskit(qc, valid_ops)
    return hook


def make_derivative_stateprep_config(
    base_config: ENDVQSStatePreparationConfig,
    derivative: str,
    derivative_index: int = 0,
) -> ENDVQSStatePreparationConfig:
    return ENDVQSStatePreparationConfig(
        electronic=base_config.electronic,
        nuclear=base_config.nuclear,
        layout=base_config.layout,
        derivative=derivative,
        derivative_index=derivative_index,
        metadata={**base_config.metadata, "derived_from": "make_derivative_stateprep_config"},
    )


def infer_derivative_for_component(component: PauliComponent) -> tuple[str | None, int | None]:
    family = component.metadata.get("component_family") if component.metadata else None
    indices = component.indices or [0]
    idx = int(indices[-1]) if indices else 0
    if family in {"Va", "Maa"}:
        return "p", idx
    if family in {"Vb", "Mbb", "Mab"}:
        return "q", idx
    if component.quantity == "M":
        return "alpha", idx
    if component.quantity == "V":
        return "p", idx
    return None, None


def make_component_specific_stateprep_plan(
    base_config: ENDVQSStatePreparationConfig,
    component: PauliComponent,
) -> StatePreparationPlan:
    derivative, idx = infer_derivative_for_component(component)
    cfg = make_derivative_stateprep_config(base_config, derivative, idx) if derivative else base_config
    return make_endvqs_stateprep_plan(cfg, component=component)


def export_stateprep_plan_json(plan: StatePreparationPlan, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(plan), indent=2, default=str), encoding="utf-8")
    return path


def export_stateprep_operations_csv(plan: StatePreparationPlan, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["gate", "qubits", "parameter", "label"])
        for op in plan.operations:
            writer.writerow([op.gate, json.dumps(op.qubits), op.parameter, op.label])
    return path


def make_stateprep_report(plan: StatePreparationPlan, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.7 END/VQS State-Preparation Report",
        "",
        "## Summary",
        "",
        "```text",
        plan.summary(),
        "```",
        "",
        "## Configuration",
        "",
        "```text",
        plan.config.summary(),
        "```",
        "",
        "## Operations",
        "",
    ]
    for op in plan.operations:
        lines.append(f"- `{op.summary()}`")
    lines.extend([
        "",
        "## Scientific note",
        "",
        "The v3.7 state-preparation hooks are scaffold implementations for END/VQS circuit assembly. Replace or refine these operations with the exact Fukutome/coherent-state constructions required by the final derivation.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_stateprep_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = ENDVQSStatePreparationConfig()
    component = PauliComponent(
        name="demo_Mbb_00",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(0.5, "ZI"), PauliTerm(-0.25, "IZ"), PauliTerm(0.1, "XX")],
        metadata={"component_family": "Mbb"},
    )
    plan = make_component_specific_stateprep_plan(config, component)
    artifacts = {
        "stateprep_config_json": str(save_stateprep_config(config, output_dir / "stateprep_config.json")),
        "stateprep_plan_json": str(export_stateprep_plan_json(plan, output_dir / "stateprep_plan.json")),
        "stateprep_operations_csv": str(export_stateprep_operations_csv(plan, output_dir / "stateprep_operations.csv")),
        "stateprep_report": str(make_stateprep_report(plan, output_dir / "stateprep_report.md")),
    }
    manifest_path = output_dir / "stateprep_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.7 END/VQS state preparation",
        "plan_summary": plan.summary(),
        "artifacts": artifacts,
    }, indent=2), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)
    return plan, artifacts


def run_endvqs_qiskit_component_execution(
    component: PauliComponent,
    stateprep_config: ENDVQSStatePreparationConfig | None = None,
    backend: str = "fallback",
    shots: int = 1024,
):
    stateprep_config = stateprep_config or ENDVQSStatePreparationConfig()
    plan = make_component_specific_stateprep_plan(stateprep_config, component)
    hook = make_qiskit_stateprep_hook(plan)
    qcfg = QiskitExecutionConfig(backend=backend, shots=shots)
    execution = execute_component_with_qiskit_or_fallback(component, qcfg, state_preparation_hook=hook)
    backend_used = execution.group_results[0].backend_used if execution.group_results else backend
    return ENDVQSExecutionResult(
        component_name=component.name,
        stateprep_plan=plan,
        component_execution_summary=execution.summary(),
        estimate_real=execution.component_estimate.estimate.real,
        estimate_imag=execution.component_estimate.estimate.imag,
        backend_used=backend_used,
        metadata={
            "n_groups": len(execution.group_results),
            "quantity": component.quantity,
            "family": component.metadata.get("component_family") if component.metadata else None,
        },
    ), execution


def run_production_endvqs_execution(
    spec_or_path,
    stateprep_config_path: str | None = None,
    backend: str = "fallback",
    max_components: int | None = None,
    shots: int | None = None,
):
    if isinstance(spec_or_path, (str, Path)):
        spec = load_production_spec(spec_or_path)
    else:
        spec = spec_or_path

    stateprep_config = load_stateprep_config(stateprep_config_path) if stateprep_config_path else ENDVQSStatePreparationConfig()
    output_dir = Path(spec.output_dir) / "endvqs_stateprep_execution"
    output_dir.mkdir(parents=True, exist_ok=True)

    components = load_selected_pauli_components(spec, max_components=max_components)
    results = []
    execution_summaries = []
    artifacts = {}

    for component in components:
        result, execution = run_endvqs_qiskit_component_execution(
            component,
            stateprep_config=stateprep_config,
            backend=backend,
            shots=int(shots or spec.execution_policy.shots),
        )
        results.append(result)
        execution_summaries.append(execution)

        comp_dir = output_dir / component.name
        comp_dir.mkdir(parents=True, exist_ok=True)
        artifacts[f"{component.name}_stateprep_plan"] = str(export_stateprep_plan_json(result.stateprep_plan, comp_dir / "stateprep_plan.json"))
        artifacts[f"{component.name}_stateprep_ops"] = str(export_stateprep_operations_csv(result.stateprep_plan, comp_dir / "stateprep_operations.csv"))
        artifacts[f"{component.name}_stateprep_report"] = str(make_stateprep_report(result.stateprep_plan, comp_dir / "stateprep_report.md"))

    artifacts["endvqs_execution_results_csv"] = str(export_endvqs_execution_results_csv(results, output_dir / "endvqs_execution_results.csv"))
    artifacts["endvqs_execution_results_json"] = str(export_endvqs_execution_results_json(results, output_dir / "endvqs_execution_results.json"))
    artifacts["endvqs_execution_report"] = str(make_endvqs_execution_report(results, output_dir / "endvqs_stateprep_execution_report.md"))

    manifest_path = output_dir / "endvqs_stateprep_execution_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.7 END/VQS state-prep execution",
        "project": spec.project_name,
        "backend": backend,
        "results": [asdict(r) for r in results],
        "artifacts": artifacts,
    }, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return {
        "spec": spec,
        "stateprep_config": stateprep_config,
        "results": results,
        "execution_summaries": execution_summaries,
        "artifacts": artifacts,
    }


def export_endvqs_execution_results_csv(results: list[ENDVQSExecutionResult], path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["component_name", "estimate_real", "estimate_imag", "backend_used", "n_operations"])
        for r in results:
            writer.writerow([
                r.component_name,
                r.estimate_real,
                r.estimate_imag,
                r.backend_used,
                len(r.stateprep_plan.operations),
            ])
    return path


def export_endvqs_execution_results_json(results: list[ENDVQSExecutionResult], path):
    path = Path(path)
    path.write_text(json.dumps([asdict(r) for r in results], indent=2, default=str), encoding="utf-8")
    return path


def make_endvqs_execution_report(results: list[ENDVQSExecutionResult], output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.7 END/VQS State-Preparation Execution Report",
        "",
        "## Summary",
        "",
        f"- Components executed: **{len(results)}**",
        "",
        "## Results",
        "",
    ]
    for result in results:
        lines.extend(["```text", result.summary(), "```", ""])
    lines.extend([
        "## Scientific note",
        "",
        "These END/VQS state-preparation hooks are scaffolds. Final production should use the exact electronic Fukutome and nuclear coherent-state unitaries from the derivation.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
