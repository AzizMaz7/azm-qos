from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import copy
import csv
import json
import math
import time

from .pauli_compiler import PauliComponent, PauliTerm
from .production import load_production_spec
from .production_pauli_execution import load_selected_pauli_components
from .endvqs_stateprep import (
    ENDVQSStatePreparationConfig,
    ElectronicStateParameters,
    NuclearCoherentParameters,
    ENDVQSLayout,
    load_stateprep_config,
    save_stateprep_config,
    run_endvqs_qiskit_component_execution,
)


@dataclass
class DerivativeParameter:
    name: str
    index: int = 0

    def key(self) -> str:
        return f"{self.name}[{self.index}]"

    def summary(self) -> str:
        return f"DerivativeParameter(name={self.name}, index={self.index})"


@dataclass
class DerivativeEstimatorConfig:
    parameters: list[DerivativeParameter] = field(default_factory=lambda: [
        DerivativeParameter("p", 0),
        DerivativeParameter("q", 0),
        DerivativeParameter("alpha", 0),
        DerivativeParameter("beta", 0),
    ])
    shift: float = math.pi / 2.0
    finite_difference_step: float = 1.0e-3
    shots: int = 1024
    backend: str = "fallback"
    uncertainty_shot_floor: float = 1.0e-12

    def summary(self) -> str:
        return (
            "DerivativeEstimatorConfig\n"
            f"  parameters: {[p.key() for p in self.parameters]}\n"
            f"  shift: {self.shift}\n"
            f"  finite_difference_step: {self.finite_difference_step}\n"
            f"  shots: {self.shots}\n"
            f"  backend: {self.backend}"
        )


@dataclass
class ComponentDerivativeEstimate:
    component_name: str
    quantity: str
    family: str | None
    indices: list[int]
    parameter: DerivativeParameter
    base_value: float
    plus_value: float
    minus_value: float
    parameter_shift_derivative: float
    finite_difference_derivative: float
    absolute_difference: float
    uncertainty: float
    backend: str
    shots: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ComponentDerivativeEstimate\n"
            f"  component: {self.component_name}\n"
            f"  parameter: {self.parameter.key()}\n"
            f"  base: {self.base_value:+.10f}\n"
            f"  plus: {self.plus_value:+.10f}\n"
            f"  minus: {self.minus_value:+.10f}\n"
            f"  parameter_shift: {self.parameter_shift_derivative:+.10f}\n"
            f"  finite_difference: {self.finite_difference_derivative:+.10f}\n"
            f"  abs_diff: {self.absolute_difference:.8e}\n"
            f"  uncertainty: {self.uncertainty:.8e}"
        )


@dataclass
class ProductionDerivativeResult:
    project_name: str
    component_derivatives: list[ComponentDerivativeEstimate]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        by_param = {}
        for item in self.component_derivatives:
            by_param[item.parameter.key()] = by_param.get(item.parameter.key(), 0) + 1
        return (
            "ProductionDerivativeResult\n"
            f"  project: {self.project_name}\n"
            f"  derivative_estimates: {len(self.component_derivatives)}\n"
            f"  by_parameter: {by_param}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def derivative_parameters_from_dicts(items: list[dict[str, Any]]) -> list[DerivativeParameter]:
    return [DerivativeParameter(name=str(x["name"]), index=int(x.get("index", 0))) for x in items]


def get_parameter_vector(config: ENDVQSStatePreparationConfig, name: str) -> list[float]:
    name = name.lower()
    if name == "alpha":
        return config.electronic.alpha
    if name == "beta":
        return config.electronic.beta
    if name == "p":
        return config.nuclear.p
    if name == "q":
        return config.nuclear.q
    raise KeyError(f"Unknown parameter name: {name}")


def get_parameter_value(config: ENDVQSStatePreparationConfig, parameter: DerivativeParameter) -> float:
    vec = get_parameter_vector(config, parameter.name)
    if not vec:
        raise IndexError(f"Parameter vector {parameter.name} is empty.")
    return float(vec[parameter.index % len(vec)])


def set_parameter_value(config: ENDVQSStatePreparationConfig, parameter: DerivativeParameter, value: float) -> ENDVQSStatePreparationConfig:
    cfg = copy.deepcopy(config)
    vec = get_parameter_vector(cfg, parameter.name)
    if not vec:
        raise IndexError(f"Parameter vector {parameter.name} is empty.")
    vec[parameter.index % len(vec)] = float(value)
    return cfg


def shifted_stateprep_config(
    config: ENDVQSStatePreparationConfig,
    parameter: DerivativeParameter,
    delta: float,
) -> ENDVQSStatePreparationConfig:
    base = get_parameter_value(config, parameter)
    return set_parameter_value(config, parameter, base + delta)


def component_family(component: PauliComponent) -> str | None:
    return component.metadata.get("component_family") if component.metadata else None


def evaluate_component_value(
    component: PauliComponent,
    stateprep_config: ENDVQSStatePreparationConfig,
    backend: str = "fallback",
    shots: int = 1024,
) -> float:
    result, _execution = run_endvqs_qiskit_component_execution(
        component,
        stateprep_config=stateprep_config,
        backend=backend,
        shots=shots,
    )
    return float(result.estimate_real)


def estimate_uncertainty_from_values(plus_value: float, minus_value: float, shots: int, scale: float) -> float:
    # Shot-noise-style scaffold: bounded observable standard error propagated through a two-point difference.
    if shots <= 0:
        return float("nan")
    var_plus = max(0.0, 1.0 - min(1.0, abs(plus_value)) ** 2) / shots
    var_minus = max(0.0, 1.0 - min(1.0, abs(minus_value)) ** 2) / shots
    return abs(scale) * math.sqrt(var_plus + var_minus)


def estimate_component_derivative(
    component: PauliComponent,
    base_config: ENDVQSStatePreparationConfig,
    parameter: DerivativeParameter,
    estimator_config: DerivativeEstimatorConfig,
) -> ComponentDerivativeEstimate:
    base_parameter_value = get_parameter_value(base_config, parameter)

    base_value = evaluate_component_value(
        component,
        base_config,
        backend=estimator_config.backend,
        shots=estimator_config.shots,
    )

    plus_cfg = shifted_stateprep_config(base_config, parameter, estimator_config.shift)
    minus_cfg = shifted_stateprep_config(base_config, parameter, -estimator_config.shift)
    plus_value = evaluate_component_value(component, plus_cfg, backend=estimator_config.backend, shots=estimator_config.shots)
    minus_value = evaluate_component_value(component, minus_cfg, backend=estimator_config.backend, shots=estimator_config.shots)
    parameter_shift = 0.5 * (plus_value - minus_value)

    h = estimator_config.finite_difference_step
    fd_plus = evaluate_component_value(component, shifted_stateprep_config(base_config, parameter, h), backend=estimator_config.backend, shots=estimator_config.shots)
    fd_minus = evaluate_component_value(component, shifted_stateprep_config(base_config, parameter, -h), backend=estimator_config.backend, shots=estimator_config.shots)
    finite_difference = (fd_plus - fd_minus) / (2.0 * h)

    uncertainty = estimate_uncertainty_from_values(
        plus_value,
        minus_value,
        estimator_config.shots,
        scale=0.5,
    )

    return ComponentDerivativeEstimate(
        component_name=component.name,
        quantity=component.quantity,
        family=component_family(component),
        indices=list(component.indices),
        parameter=parameter,
        base_value=base_value,
        plus_value=plus_value,
        minus_value=minus_value,
        parameter_shift_derivative=parameter_shift,
        finite_difference_derivative=finite_difference,
        absolute_difference=abs(parameter_shift - finite_difference),
        uncertainty=uncertainty,
        backend=estimator_config.backend,
        shots=estimator_config.shots,
        metadata={
            "base_parameter_value": base_parameter_value,
            "finite_difference_step": estimator_config.finite_difference_step,
            "shift": estimator_config.shift,
        },
    )


def estimate_component_derivatives(
    component: PauliComponent,
    base_config: ENDVQSStatePreparationConfig,
    estimator_config: DerivativeEstimatorConfig,
) -> list[ComponentDerivativeEstimate]:
    return [
        estimate_component_derivative(component, base_config, parameter, estimator_config)
        for parameter in estimator_config.parameters
    ]


def export_derivative_estimates_csv(estimates: list[ComponentDerivativeEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "component_name", "quantity", "family", "indices", "parameter",
            "base_value", "plus_value", "minus_value", "parameter_shift_derivative",
            "finite_difference_derivative", "absolute_difference", "uncertainty",
            "backend", "shots"
        ])
        for e in estimates:
            writer.writerow([
                e.component_name,
                e.quantity,
                e.family,
                json.dumps(e.indices),
                e.parameter.key(),
                e.base_value,
                e.plus_value,
                e.minus_value,
                e.parameter_shift_derivative,
                e.finite_difference_derivative,
                e.absolute_difference,
                e.uncertainty,
                e.backend,
                e.shots,
            ])
    return path


def export_derivative_estimates_json(estimates: list[ComponentDerivativeEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(e) for e in estimates], indent=2, default=str), encoding="utf-8")
    return path


def export_derivative_summary_tables(estimates: list[ComponentDerivativeEstimate], output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    m_path = output_dir / "M_derivatives.csv"
    v_path = output_dir / "V_derivatives.csv"

    for quantity, path in [("M", m_path), ("V", v_path)]:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "component_name", "family", "indices", "parameter",
                "parameter_shift_derivative", "finite_difference_derivative",
                "absolute_difference", "uncertainty"
            ])
            for e in estimates:
                if e.quantity == quantity:
                    writer.writerow([
                        e.component_name,
                        e.family,
                        json.dumps(e.indices),
                        e.parameter.key(),
                        e.parameter_shift_derivative,
                        e.finite_difference_derivative,
                        e.absolute_difference,
                        e.uncertainty,
                    ])

    return {"M_derivatives_csv": str(m_path), "V_derivatives_csv": str(v_path)}


def plot_derivative_comparison(estimates: list[ComponentDerivativeEstimate], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(e.summary() for e in estimates), encoding="utf-8")
        return txt

    labels = [f"{e.component_name}:{e.parameter.key()}" for e in estimates]
    ps = [e.parameter_shift_derivative for e in estimates]
    fd = [e.finite_difference_derivative for e in estimates]
    x = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, ps, marker="o", label="parameter-shift")
    ax.plot(x, fd, marker="s", label="finite-difference")
    ax.set_xlabel("component derivative")
    ax.set_ylabel("derivative estimate")
    ax.set_title("Parameter-shift vs finite-difference derivatives")
    if len(labels) <= 12:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def make_derivative_report(result: ProductionDerivativeResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.8 Parameter-Shift and Derivative Estimator Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Derivative estimates",
        "",
    ]
    for estimate in result.component_derivatives:
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
        "The v3.8 derivative workflow compares parameter-shift-style estimates with central finite differences using the current END/VQS state-preparation scaffold. Replace scaffold state preparation with the exact END/VQS unitaries before using derivative values as final scientific results.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_derivative_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    component = PauliComponent(
        name="demo_derivative_Mbb_00",
        quantity="M",
        indices=[0, 0],
        terms=[
            PauliTerm(0.5, "ZI"),
            PauliTerm(-0.25, "IZ"),
            PauliTerm(0.1, "XX"),
        ],
        metadata={"component_family": "Mbb"},
    )
    base_config = ENDVQSStatePreparationConfig()
    estimator_config = DerivativeEstimatorConfig(
        parameters=[DerivativeParameter("p", 0), DerivativeParameter("q", 0)],
        shots=256,
        backend="fallback",
    )
    estimates = estimate_component_derivatives(component, base_config, estimator_config)

    artifacts = {}
    artifacts["derivative_estimates_csv"] = str(export_derivative_estimates_csv(estimates, output_dir / "derivative_estimates.csv"))
    artifacts["derivative_estimates_json"] = str(export_derivative_estimates_json(estimates, output_dir / "derivative_estimates.json"))
    artifacts.update(export_derivative_summary_tables(estimates, output_dir))
    artifacts["derivative_comparison_figure"] = str(plot_derivative_comparison(estimates, output_dir / "derivative_comparison.png"))

    result = ProductionDerivativeResult(
        project_name="derivative_demo",
        component_derivatives=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
        metadata={"estimator_config": asdict(estimator_config)},
    )
    artifacts["derivative_report"] = str(make_derivative_report(result, output_dir / "derivative_report.md"))

    manifest_path = output_dir / "derivative_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.8 derivative demo",
        "summary": result.summary(),
        "artifacts": artifacts,
    }, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionDerivativeResult(
        project_name="derivative_demo",
        component_derivatives=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
        metadata={"estimator_config": asdict(estimator_config)},
    )


def run_production_derivative_estimators(
    spec_or_path,
    stateprep_config_path: str | None = None,
    backend: str = "fallback",
    max_components: int | None = None,
    shots: int | None = None,
    parameters: list[DerivativeParameter] | None = None,
):
    if isinstance(spec_or_path, (str, Path)):
        spec = load_production_spec(spec_or_path)
    else:
        spec = spec_or_path

    base_config = load_stateprep_config(stateprep_config_path) if stateprep_config_path else ENDVQSStatePreparationConfig()
    output_dir = Path(spec.output_dir) / "derivative_estimators"
    output_dir.mkdir(parents=True, exist_ok=True)

    components = load_selected_pauli_components(spec, max_components=max_components)
    warnings = []
    if not components:
        warnings.append("No components selected for derivative estimation.")

    estimator_config = DerivativeEstimatorConfig(
        parameters=parameters or [DerivativeParameter("p", 0), DerivativeParameter("q", 0), DerivativeParameter("alpha", 0), DerivativeParameter("beta", 0)],
        shots=int(shots or spec.execution_policy.shots),
        backend=backend,
    )

    estimates: list[ComponentDerivativeEstimate] = []
    for component in components:
        estimates.extend(estimate_component_derivatives(component, base_config, estimator_config))

    artifacts = {}
    artifacts["derivative_estimates_csv"] = str(export_derivative_estimates_csv(estimates, output_dir / "derivative_estimates.csv"))
    artifacts["derivative_estimates_json"] = str(export_derivative_estimates_json(estimates, output_dir / "derivative_estimates.json"))
    artifacts.update(export_derivative_summary_tables(estimates, output_dir))
    artifacts["derivative_comparison_figure"] = str(plot_derivative_comparison(estimates, output_dir / "derivative_comparison.png"))

    result = ProductionDerivativeResult(
        project_name=spec.project_name,
        component_derivatives=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"estimator_config": asdict(estimator_config)},
    )
    artifacts["derivative_report"] = str(make_derivative_report(result, output_dir / "derivative_report.md"))

    manifest_path = output_dir / "production_derivatives_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.8 production derivative estimators",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": warnings,
        "artifacts": artifacts,
    }, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionDerivativeResult(
        project_name=spec.project_name,
        component_derivatives=estimates,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=warnings,
        metadata={"estimator_config": asdict(estimator_config)},
    )
