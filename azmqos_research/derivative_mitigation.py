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
from .endvqs_stateprep import ENDVQSStatePreparationConfig, load_stateprep_config
from .derivative_estimators import (
    DerivativeParameter,
    DerivativeEstimatorConfig,
    ComponentDerivativeEstimate,
    ProductionDerivativeResult,
    estimate_component_derivatives,
    run_production_derivative_estimators,
    export_derivative_estimates_csv,
    export_derivative_estimates_json,
    export_derivative_summary_tables,
    plot_derivative_comparison,
    make_derivative_report,
)


@dataclass
class ReadoutCalibration:
    assignment_matrix: list[list[float]]
    labels: list[str] = field(default_factory=lambda: ["0", "1"])
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ReadoutCalibration\n"
            f"  labels: {self.labels}\n"
            f"  assignment_matrix: {self.assignment_matrix}"
        )


@dataclass
class ZNEConfig:
    noise_factors: list[float] = field(default_factory=lambda: [1.0, 3.0, 5.0])
    fit_order: int = 1

    def summary(self) -> str:
        return f"ZNEConfig(noise_factors={self.noise_factors}, fit_order={self.fit_order})"


@dataclass
class MitigatedDerivativeEstimate:
    raw: ComponentDerivativeEstimate
    readout_mitigated_derivative: float
    zne_derivative: float
    combined_derivative: float
    propagated_uncertainty: float
    shot_allocation: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "MitigatedDerivativeEstimate\n"
            f"  component: {self.raw.component_name}\n"
            f"  parameter: {self.raw.parameter.key()}\n"
            f"  raw_parameter_shift: {self.raw.parameter_shift_derivative:+.10f}\n"
            f"  readout_mitigated: {self.readout_mitigated_derivative:+.10f}\n"
            f"  zne: {self.zne_derivative:+.10f}\n"
            f"  combined: {self.combined_derivative:+.10f}\n"
            f"  uncertainty: {self.propagated_uncertainty:.8e}"
        )


@dataclass
class ProductionDerivativeMitigationResult:
    project_name: str
    raw_derivatives: list[ComponentDerivativeEstimate]
    mitigated_derivatives: list[MitigatedDerivativeEstimate]
    output_dir: str
    artifacts: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        by_param = {}
        for item in self.mitigated_derivatives:
            by_param[item.raw.parameter.key()] = by_param.get(item.raw.parameter.key(), 0) + 1
        return (
            "ProductionDerivativeMitigationResult\n"
            f"  project: {self.project_name}\n"
            f"  raw_derivatives: {len(self.raw_derivatives)}\n"
            f"  mitigated_derivatives: {len(self.mitigated_derivatives)}\n"
            f"  by_parameter: {by_param}\n"
            f"  artifacts: {len(self.artifacts)}\n"
            f"  warnings: {self.warnings}"
        )


def default_single_qubit_calibration(p00: float = 0.97, p11: float = 0.96) -> ReadoutCalibration:
    return ReadoutCalibration(
        assignment_matrix=[
            [float(p00), 1.0 - float(p11)],
            [1.0 - float(p00), float(p11)],
        ],
        labels=["0", "1"],
        metadata={"description": "Default single-qubit readout assignment matrix."},
    )


def invert_2x2(matrix: list[list[float]]) -> list[list[float]]:
    a, b = matrix[0]
    c, d = matrix[1]
    det = a * d - b * c
    if abs(det) < 1e-15:
        raise ValueError("Calibration matrix is singular or nearly singular.")
    return [[d / det, -b / det], [-c / det, a / det]]


def apply_readout_mitigation_to_binary_probs(
    observed_probs: list[float],
    calibration: ReadoutCalibration,
) -> list[float]:
    inv = invert_2x2(calibration.assignment_matrix)
    mitigated = [
        inv[0][0] * observed_probs[0] + inv[0][1] * observed_probs[1],
        inv[1][0] * observed_probs[0] + inv[1][1] * observed_probs[1],
    ]
    clipped = [max(0.0, min(1.0, x)) for x in mitigated]
    norm = sum(clipped)
    if norm <= 0:
        return [0.5, 0.5]
    return [x / norm for x in clipped]


def mitigate_expectation_value(
    observed_expectation: float,
    calibration: ReadoutCalibration | None = None,
) -> float:
    calibration = calibration or default_single_qubit_calibration()
    p0 = 0.5 * (1.0 + observed_expectation)
    p1 = 1.0 - p0
    m0, m1 = apply_readout_mitigation_to_binary_probs([p0, p1], calibration)
    return float(max(-1.0, min(1.0, m0 - m1)))


def mitigate_derivative_readout(
    estimate: ComponentDerivativeEstimate,
    calibration: ReadoutCalibration | None = None,
) -> float:
    plus = mitigate_expectation_value(estimate.plus_value, calibration)
    minus = mitigate_expectation_value(estimate.minus_value, calibration)
    return 0.5 * (plus - minus)


def synthetic_noise_scaled_derivatives(
    raw_derivative: float,
    noise_factors: list[float],
    damping: float = 0.035,
) -> list[tuple[float, float]]:
    # Deterministic ZNE scaffold: larger noise factors damp the magnitude.
    return [(f, raw_derivative * math.exp(-damping * (f - 1.0))) for f in noise_factors]


def linear_zne_extrapolate(points: list[tuple[float, float]]) -> float:
    if len(points) == 1:
        return points[0][1]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-15:
        return ys[0]
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    # Evaluate fitted line at zero noise factor.
    return float(intercept)


def zne_derivative_estimate(
    estimate: ComponentDerivativeEstimate,
    zne_config: ZNEConfig | None = None,
) -> float:
    zne_config = zne_config or ZNEConfig()
    points = synthetic_noise_scaled_derivatives(
        estimate.parameter_shift_derivative,
        zne_config.noise_factors,
    )
    return linear_zne_extrapolate(points)


def propagate_derivative_uncertainty(
    estimate: ComponentDerivativeEstimate,
    readout_mitigated: float,
    zne_value: float,
) -> float:
    raw_unc = float(estimate.uncertainty)
    readout_spread = abs(readout_mitigated - estimate.parameter_shift_derivative)
    zne_spread = abs(zne_value - estimate.parameter_shift_derivative)
    return math.sqrt(raw_unc * raw_unc + 0.25 * readout_spread * readout_spread + 0.25 * zne_spread * zne_spread)


def allocate_derivative_shots(
    estimates: list[ComponentDerivativeEstimate],
    total_shots: int,
    min_shots: int = 32,
) -> dict[str, int]:
    if not estimates:
        return {}
    weights = []
    for estimate in estimates:
        weights.append(max(estimate.uncertainty, 1e-12))
    total_weight = sum(weights)
    allocation = {}
    remaining = int(total_shots)
    for estimate, weight in zip(estimates, weights):
        key = f"{estimate.component_name}:{estimate.parameter.key()}"
        n = max(min_shots, int(round(total_shots * weight / total_weight)))
        allocation[key] = n
        remaining -= n
    # Adjust first key to conserve total_shots when possible.
    if allocation:
        first = next(iter(allocation))
        allocation[first] = max(min_shots, allocation[first] + remaining)
    return allocation


def mitigate_derivative_estimate(
    estimate: ComponentDerivativeEstimate,
    calibration: ReadoutCalibration | None = None,
    zne_config: ZNEConfig | None = None,
    shot_allocation: dict[str, int] | None = None,
) -> MitigatedDerivativeEstimate:
    readout_value = mitigate_derivative_readout(estimate, calibration)
    zne_value = zne_derivative_estimate(estimate, zne_config)
    combined = 0.5 * (readout_value + zne_value)
    uncertainty = propagate_derivative_uncertainty(estimate, readout_value, zne_value)
    key = f"{estimate.component_name}:{estimate.parameter.key()}"
    return MitigatedDerivativeEstimate(
        raw=estimate,
        readout_mitigated_derivative=readout_value,
        zne_derivative=zne_value,
        combined_derivative=combined,
        propagated_uncertainty=uncertainty,
        shot_allocation={key: (shot_allocation or {}).get(key, estimate.shots)},
        metadata={
            "calibration": (calibration or default_single_qubit_calibration()).summary(),
            "zne_config": (zne_config or ZNEConfig()).summary(),
        },
    )


def mitigate_derivative_estimates(
    estimates: list[ComponentDerivativeEstimate],
    calibration: ReadoutCalibration | None = None,
    zne_config: ZNEConfig | None = None,
    total_shots: int | None = None,
) -> list[MitigatedDerivativeEstimate]:
    allocation = allocate_derivative_shots(estimates, total_shots or sum(e.shots for e in estimates))
    return [
        mitigate_derivative_estimate(e, calibration=calibration, zne_config=zne_config, shot_allocation=allocation)
        for e in estimates
    ]


def export_mitigated_derivatives_csv(estimates: list[MitigatedDerivativeEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "component_name", "quantity", "family", "indices", "parameter",
            "raw_parameter_shift", "readout_mitigated_derivative", "zne_derivative",
            "combined_derivative", "propagated_uncertainty", "backend", "shots"
        ])
        for e in estimates:
            writer.writerow([
                e.raw.component_name,
                e.raw.quantity,
                e.raw.family,
                json.dumps(e.raw.indices),
                e.raw.parameter.key(),
                e.raw.parameter_shift_derivative,
                e.readout_mitigated_derivative,
                e.zne_derivative,
                e.combined_derivative,
                e.propagated_uncertainty,
                e.raw.backend,
                e.raw.shots,
            ])
    return path


def export_mitigated_derivatives_json(estimates: list[MitigatedDerivativeEstimate], path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(e) for e in estimates], indent=2, default=str), encoding="utf-8")
    return path


def export_mitigated_mv_tables(estimates: list[MitigatedDerivativeEstimate], output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    m_path = output_dir / "M_mitigated_derivatives.csv"
    v_path = output_dir / "V_mitigated_derivatives.csv"

    for quantity, path in [("M", m_path), ("V", v_path)]:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "component_name", "family", "indices", "parameter",
                "combined_derivative", "propagated_uncertainty",
                "readout_mitigated_derivative", "zne_derivative"
            ])
            for e in estimates:
                if e.raw.quantity == quantity:
                    writer.writerow([
                        e.raw.component_name,
                        e.raw.family,
                        json.dumps(e.raw.indices),
                        e.raw.parameter.key(),
                        e.combined_derivative,
                        e.propagated_uncertainty,
                        e.readout_mitigated_derivative,
                        e.zne_derivative,
                    ])
    return {"M_mitigated_derivatives_csv": str(m_path), "V_mitigated_derivatives_csv": str(v_path)}


def plot_mitigated_derivative_comparison(estimates: list[MitigatedDerivativeEstimate], path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text("\n".join(e.summary() for e in estimates), encoding="utf-8")
        return txt

    labels = [f"{e.raw.component_name}:{e.raw.parameter.key()}" for e in estimates]
    raw = [e.raw.parameter_shift_derivative for e in estimates]
    combined = [e.combined_derivative for e in estimates]
    x = list(range(len(labels)))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, raw, marker="o", label="raw")
    ax.plot(x, combined, marker="s", label="mitigated")
    ax.set_xlabel("component derivative")
    ax.set_ylabel("derivative")
    ax.set_title("Raw vs mitigated derivative estimates")
    if len(labels) <= 12:
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def make_derivative_mitigation_report(result: ProductionDerivativeMitigationResult, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v3.9 Derivative Error-Mitigation Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Mitigated derivative estimates",
        "",
    ]
    for estimate in result.mitigated_derivatives:
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
        "The v3.9 mitigation workflow is a scaffold for readout mitigation, ZNE-style derivative extrapolation, and uncertainty propagation. Replace mock calibration/noise models with device-specific calibration data before using results as final hardware estimates.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_derivative_mitigation_demo(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    component = PauliComponent(
        name="demo_mitigated_derivative_Mbb_00",
        quantity="M",
        indices=[0, 0],
        terms=[PauliTerm(0.5, "ZI"), PauliTerm(-0.25, "IZ"), PauliTerm(0.1, "XX")],
        metadata={"component_family": "Mbb"},
    )
    from .derivative_estimators import DerivativeParameter, DerivativeEstimatorConfig, estimate_component_derivatives

    raw = estimate_component_derivatives(
        component,
        ENDVQSStatePreparationConfig(),
        DerivativeEstimatorConfig(
            parameters=[DerivativeParameter("p", 0), DerivativeParameter("q", 0)],
            shots=256,
            backend="fallback",
        ),
    )
    mitigated = mitigate_derivative_estimates(raw)

    artifacts = {}
    artifacts["raw_derivatives_csv"] = str(export_derivative_estimates_csv(raw, output_dir / "raw_derivatives.csv"))
    artifacts["mitigated_derivatives_csv"] = str(export_mitigated_derivatives_csv(mitigated, output_dir / "mitigated_derivatives.csv"))
    artifacts["mitigated_derivatives_json"] = str(export_mitigated_derivatives_json(mitigated, output_dir / "mitigated_derivatives.json"))
    artifacts.update(export_mitigated_mv_tables(mitigated, output_dir))
    artifacts["mitigation_comparison_figure"] = str(plot_mitigated_derivative_comparison(mitigated, output_dir / "mitigation_comparison.png"))

    result = ProductionDerivativeMitigationResult(
        project_name="derivative_mitigation_demo",
        raw_derivatives=raw,
        mitigated_derivatives=mitigated,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )
    artifacts["mitigation_report"] = str(make_derivative_mitigation_report(result, output_dir / "derivative_mitigation_report.md"))

    manifest_path = output_dir / "derivative_mitigation_demo_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.9 derivative mitigation demo",
        "summary": result.summary(),
        "artifacts": artifacts,
    }, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionDerivativeMitigationResult(
        project_name="derivative_mitigation_demo",
        raw_derivatives=raw,
        mitigated_derivatives=mitigated,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=[],
    )


def run_production_mitigated_derivatives(
    spec_or_path,
    stateprep_config_path: str | None = None,
    backend: str = "fallback",
    max_components: int | None = None,
    shots: int | None = None,
    total_allocation_shots: int | None = None,
):
    if isinstance(spec_or_path, (str, Path)):
        spec = load_production_spec(spec_or_path)
    else:
        spec = spec_or_path

    raw_result = run_production_derivative_estimators(
        spec,
        stateprep_config_path=stateprep_config_path,
        backend=backend,
        max_components=max_components,
        shots=shots,
    )
    raw = raw_result.component_derivatives
    mitigated = mitigate_derivative_estimates(
        raw,
        calibration=default_single_qubit_calibration(),
        zne_config=ZNEConfig(),
        total_shots=total_allocation_shots,
    )

    output_dir = Path(spec.output_dir) / "derivative_mitigation"
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {}
    artifacts["raw_derivatives_csv"] = str(export_derivative_estimates_csv(raw, output_dir / "raw_derivatives.csv"))
    artifacts["raw_derivatives_json"] = str(export_derivative_estimates_json(raw, output_dir / "raw_derivatives.json"))
    artifacts["mitigated_derivatives_csv"] = str(export_mitigated_derivatives_csv(mitigated, output_dir / "mitigated_derivatives.csv"))
    artifacts["mitigated_derivatives_json"] = str(export_mitigated_derivatives_json(mitigated, output_dir / "mitigated_derivatives.json"))
    artifacts.update(export_mitigated_mv_tables(mitigated, output_dir))
    artifacts["mitigation_comparison_figure"] = str(plot_mitigated_derivative_comparison(mitigated, output_dir / "mitigation_comparison.png"))

    result = ProductionDerivativeMitigationResult(
        project_name=spec.project_name,
        raw_derivatives=raw,
        mitigated_derivatives=mitigated,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(raw_result.warnings),
        metadata={"raw_artifacts": raw_result.artifacts},
    )
    artifacts["mitigation_report"] = str(make_derivative_mitigation_report(result, output_dir / "derivative_mitigation_report.md"))

    manifest_path = output_dir / "production_mitigated_derivatives_manifest.json"
    manifest_path.write_text(json.dumps({
        "package": "AZM-QOS v3.9 production mitigated derivatives",
        "project": spec.project_name,
        "summary": result.summary(),
        "warnings": result.warnings,
        "artifacts": artifacts,
    }, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    return ProductionDerivativeMitigationResult(
        project_name=spec.project_name,
        raw_derivatives=raw,
        mitigated_derivatives=mitigated,
        output_dir=str(output_dir),
        artifacts=artifacts,
        warnings=list(raw_result.warnings),
        metadata={"raw_artifacts": raw_result.artifacts},
    )
