from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import csv
import json
import math
import numpy as np

try:
    from .hardware_compare import compare_counts, CountsComparisonResult
except Exception:
    compare_counts = None
    CountsComparisonResult = Any


@dataclass
class ConfidenceInterval:
    lower: float
    upper: float
    confidence_level: float = 0.95
    method: str = "unknown"

    @property
    def half_width(self) -> float:
        return 0.5 * (self.upper - self.lower)

    def summary(self) -> str:
        return (
            f"ConfidenceInterval(method={self.method}, level={self.confidence_level}, "
            f"lower={self.lower:.8f}, upper={self.upper:.8f}, half_width={self.half_width:.8f})"
        )


@dataclass
class BitstringUncertainty:
    bitstring: str
    count: int
    shots: int
    probability: float
    standard_error: float
    interval: ConfidenceInterval

    def summary(self) -> str:
        return (
            f"{self.bitstring}: count={self.count}, p={self.probability:.8f}, "
            f"se={self.standard_error:.8f}, CI=({self.interval.lower:.8f}, {self.interval.upper:.8f})"
        )


@dataclass
class CountsUncertaintyResult:
    counts: dict[str, int]
    shots: int
    bitstrings: list[BitstringUncertainty]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [f"CountsUncertaintyResult(shots={self.shots}, bitstrings={len(self.bitstrings)})"]
        for item in self.bitstrings:
            lines.append("  " + item.summary())
        return "\n".join(lines)


@dataclass
class ExpectationUncertaintyResult:
    estimate: float
    standard_error: float
    interval: ConfidenceInterval
    shots: int
    observable_map: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "ExpectationUncertaintyResult\n"
            f"  estimate: {self.estimate:+.10f}\n"
            f"  standard_error: {self.standard_error:.8e}\n"
            f"  interval: ({self.interval.lower:+.10f}, {self.interval.upper:+.10f})\n"
            f"  shots: {self.shots}\n"
            f"  method: {self.interval.method}"
        )


@dataclass
class DifferenceUncertaintyResult:
    simulator_value: float
    hardware_value: float
    difference: float
    combined_standard_error: float
    interval: ConfidenceInterval
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            "DifferenceUncertaintyResult\n"
            f"  simulator_value: {self.simulator_value:+.10f}\n"
            f"  hardware_value: {self.hardware_value:+.10f}\n"
            f"  difference: {self.difference:+.10f}\n"
            f"  combined_standard_error: {self.combined_standard_error:.8e}\n"
            f"  interval: ({self.interval.lower:+.10f}, {self.interval.upper:+.10f})"
        )


@dataclass
class UncertaintyReportData:
    simulator_counts_uncertainty: CountsUncertaintyResult | None = None
    hardware_counts_uncertainty: CountsUncertaintyResult | None = None
    simulator_expectation_uncertainty: ExpectationUncertaintyResult | None = None
    hardware_expectation_uncertainty: ExpectationUncertaintyResult | None = None
    expectation_difference_uncertainty: DifferenceUncertaintyResult | None = None
    counts_comparison: Any | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        lines = ["UncertaintyReportData"]
        if self.simulator_counts_uncertainty:
            lines.append("Simulator counts uncertainty:")
            lines.append(self.simulator_counts_uncertainty.summary())
        if self.hardware_counts_uncertainty:
            lines.append("Hardware counts uncertainty:")
            lines.append(self.hardware_counts_uncertainty.summary())
        if self.simulator_expectation_uncertainty:
            lines.append("Simulator expectation:")
            lines.append(self.simulator_expectation_uncertainty.summary())
        if self.hardware_expectation_uncertainty:
            lines.append("Hardware expectation:")
            lines.append(self.hardware_expectation_uncertainty.summary())
        if self.expectation_difference_uncertainty:
            lines.append("Difference:")
            lines.append(self.expectation_difference_uncertainty.summary())
        return "\n".join(lines)


def _z_value_for_confidence(confidence_level: float) -> float:
    # Common confidence levels; fallback to 1.96.
    table = {
        0.68: 1.0,
        0.90: 1.6448536269514722,
        0.95: 1.959963984540054,
        0.99: 2.5758293035489004,
    }
    return table.get(round(float(confidence_level), 2), 1.959963984540054)


def binomial_standard_error(probability: float, shots: int) -> float:
    if shots <= 0:
        raise ValueError("shots must be positive.")
    p = min(max(float(probability), 0.0), 1.0)
    return math.sqrt(p * (1.0 - p) / shots)


def wilson_confidence_interval(successes: int, shots: int, confidence_level: float = 0.95) -> ConfidenceInterval:
    if shots <= 0:
        raise ValueError("shots must be positive.")
    if successes < 0 or successes > shots:
        raise ValueError("successes must satisfy 0 <= successes <= shots.")

    z = _z_value_for_confidence(confidence_level)
    phat = successes / shots
    denom = 1.0 + z * z / shots
    center = (phat + z * z / (2.0 * shots)) / denom
    half = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * shots)) / shots) / denom
    return ConfidenceInterval(
        lower=max(0.0, center - half),
        upper=min(1.0, center + half),
        confidence_level=confidence_level,
        method="wilson",
    )


def counts_uncertainty(counts: dict[str, int], confidence_level: float = 0.95) -> CountsUncertaintyResult:
    clean = {str(k): int(v) for k, v in counts.items()}
    shots = sum(clean.values())
    if shots <= 0:
        raise ValueError("Total shots must be positive.")

    items = []
    for bitstring in sorted(clean):
        c = clean[bitstring]
        p = c / shots
        items.append(
            BitstringUncertainty(
                bitstring=bitstring,
                count=c,
                shots=shots,
                probability=p,
                standard_error=binomial_standard_error(p, shots),
                interval=wilson_confidence_interval(c, shots, confidence_level=confidence_level),
            )
        )

    return CountsUncertaintyResult(
        counts=clean,
        shots=shots,
        bitstrings=items,
        metadata={"confidence_level": confidence_level},
    )


def counts_to_samples(counts: dict[str, int]) -> list[str]:
    samples = []
    for bitstring, count in counts.items():
        samples.extend([str(bitstring)] * int(count))
    return samples


def expectation_from_counts(counts: dict[str, int], observable_map: dict[str, float], default_value: float = 0.0) -> float:
    shots = sum(int(v) for v in counts.values())
    if shots <= 0:
        raise ValueError("Total shots must be positive.")
    total = 0.0
    for bitstring, count in counts.items():
        total += int(count) * float(observable_map.get(str(bitstring), default_value))
    return total / shots


def bootstrap_expectation_uncertainty(
    counts: dict[str, int],
    observable_map: dict[str, float],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = 123,
    default_value: float = 0.0,
) -> ExpectationUncertaintyResult:
    if n_bootstrap <= 1:
        raise ValueError("n_bootstrap must be greater than 1.")

    samples = counts_to_samples(counts)
    shots = len(samples)
    if shots <= 0:
        raise ValueError("Total shots must be positive.")

    rng = np.random.default_rng(seed)
    values = np.asarray([float(observable_map.get(s, default_value)) for s in samples], dtype=float)
    estimate = float(values.mean())

    boot = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, shots, size=shots)
        boot.append(float(values[idx].mean()))
    boot = np.asarray(boot, dtype=float)

    alpha = 1.0 - confidence_level
    lower = float(np.quantile(boot, alpha / 2.0))
    upper = float(np.quantile(boot, 1.0 - alpha / 2.0))
    se = float(boot.std(ddof=1))

    return ExpectationUncertaintyResult(
        estimate=estimate,
        standard_error=se,
        interval=ConfidenceInterval(
            lower=lower,
            upper=upper,
            confidence_level=confidence_level,
            method="bootstrap_percentile",
        ),
        shots=shots,
        observable_map=dict(observable_map),
        metadata={"n_bootstrap": n_bootstrap, "seed": seed},
    )


def propagate_difference_uncertainty(
    simulator_value: float,
    simulator_standard_error: float,
    hardware_value: float,
    hardware_standard_error: float,
    confidence_level: float = 0.95,
) -> DifferenceUncertaintyResult:
    diff = float(hardware_value) - float(simulator_value)
    combined = math.sqrt(float(simulator_standard_error) ** 2 + float(hardware_standard_error) ** 2)
    z = _z_value_for_confidence(confidence_level)
    return DifferenceUncertaintyResult(
        simulator_value=float(simulator_value),
        hardware_value=float(hardware_value),
        difference=diff,
        combined_standard_error=combined,
        interval=ConfidenceInterval(
            lower=diff - z * combined,
            upper=diff + z * combined,
            confidence_level=confidence_level,
            method="normal_error_propagation",
        ),
    )


def parity_observable_map(n_qubits: int):
    """Return +1 for even parity, -1 for odd parity bitstrings."""
    mapping = {}
    for i in range(2 ** n_qubits):
        b = format(i, f"0{n_qubits}b")
        parity = sum(int(x) for x in b) % 2
        mapping[b] = +1.0 if parity == 0 else -1.0
    return mapping


def export_counts_uncertainty_csv(result: CountsUncertaintyResult, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "bitstring", "count", "shots", "probability", "standard_error",
            "ci_lower", "ci_upper", "confidence_level", "method"
        ])
        for item in result.bitstrings:
            writer.writerow([
                item.bitstring,
                item.count,
                item.shots,
                item.probability,
                item.standard_error,
                item.interval.lower,
                item.interval.upper,
                item.interval.confidence_level,
                item.interval.method,
            ])
    return path


def export_expectation_uncertainty_csv(result: ExpectationUncertaintyResult, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["estimate", "standard_error", "ci_lower", "ci_upper", "confidence_level", "method", "shots"])
        writer.writerow([
            result.estimate,
            result.standard_error,
            result.interval.lower,
            result.interval.upper,
            result.interval.confidence_level,
            result.interval.method,
            result.shots,
        ])
    return path


def plot_counts_uncertainty(result: CountsUncertaintyResult, path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text(result.summary(), encoding="utf-8")
        return txt

    labels = [x.bitstring for x in result.bitstrings]
    probs = [x.probability for x in result.bitstrings]
    lower_err = [max(0.0, x.probability - x.interval.lower) for x in result.bitstrings]
    upper_err = [max(0.0, x.interval.upper - x.probability) for x in result.bitstrings]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(range(len(labels)), probs, yerr=[lower_err, upper_err], capsize=4)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_xlabel("bitstring")
    ax.set_ylabel("probability")
    ax.set_title("Counts uncertainty")
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def make_uncertainty_markdown_report(data: UncertaintyReportData, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v2.6 Uncertainty Report",
        "",
        "## Summary",
        "",
        "```text",
        data.summary(),
        "```",
        "",
    ]

    if data.counts_comparison is not None:
        lines.extend([
            "## Counts comparison",
            "",
            "```text",
            data.counts_comparison.summary(),
            "```",
            "",
        ])

    lines.extend(["## Artifacts", ""])
    for key, value in data.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")

    lines.extend([
        "",
        "## Scientific note",
        "",
        "The reported intervals quantify finite-shot statistical uncertainty. They do not include systematic hardware drift, calibration bias, transpilation changes, or model error.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_uncertainty_latex_report(data: UncertaintyReportData, output_path):
    output_path = Path(output_path)
    tex = f"""
\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{booktabs}}
\\title{{AZM-QOS v2.6 Uncertainty Propagation Report}}
\\author{{AZM-QOS Automated Research Workflow}}
\\date{{\\today}}
\\begin{{document}}
\\maketitle

\\section{{Summary}}
\\begin{{verbatim}}
{data.summary()}
\\end{{verbatim}}

\\section{{Interpretation}}
The reported intervals quantify finite-shot statistical uncertainty. They do not include systematic hardware drift, calibration bias, transpilation changes, or model error.

\\end{{document}}
"""
    output_path.write_text(tex.strip() + "\n", encoding="utf-8")
    return output_path


def run_mock_uncertainty_workflow(
    output_dir,
    simulator_counts: dict[str, int] | None = None,
    hardware_counts: dict[str, int] | None = None,
    n_bootstrap: int = 500,
    confidence_level: float = 0.95,
    seed: int | None = 123,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    simulator_counts = simulator_counts or {"00": 510, "11": 514}
    hardware_counts = hardware_counts or {"00": 470, "01": 30, "10": 34, "11": 490}

    sim_counts_unc = counts_uncertainty(simulator_counts, confidence_level=confidence_level)
    hw_counts_unc = counts_uncertainty(hardware_counts, confidence_level=confidence_level)

    n_qubits = max(len(str(k)) for k in set(simulator_counts) | set(hardware_counts))
    obs = parity_observable_map(n_qubits)

    sim_exp_unc = bootstrap_expectation_uncertainty(
        simulator_counts, obs, n_bootstrap=n_bootstrap, confidence_level=confidence_level, seed=seed
    )
    hw_exp_unc = bootstrap_expectation_uncertainty(
        hardware_counts, obs, n_bootstrap=n_bootstrap, confidence_level=confidence_level, seed=None if seed is None else seed + 1
    )

    diff_unc = propagate_difference_uncertainty(
        sim_exp_unc.estimate,
        sim_exp_unc.standard_error,
        hw_exp_unc.estimate,
        hw_exp_unc.standard_error,
        confidence_level=confidence_level,
    )

    comparison = compare_counts(simulator_counts, hardware_counts) if compare_counts is not None else None

    data = UncertaintyReportData(
        simulator_counts_uncertainty=sim_counts_unc,
        hardware_counts_uncertainty=hw_counts_unc,
        simulator_expectation_uncertainty=sim_exp_unc,
        hardware_expectation_uncertainty=hw_exp_unc,
        expectation_difference_uncertainty=diff_unc,
        counts_comparison=comparison,
        artifacts={},
        metadata={"n_bootstrap": n_bootstrap, "confidence_level": confidence_level},
    )

    artifacts = {}
    artifacts["simulator_counts_uncertainty_csv"] = str(export_counts_uncertainty_csv(sim_counts_unc, output_dir / "simulator_counts_uncertainty.csv"))
    artifacts["hardware_counts_uncertainty_csv"] = str(export_counts_uncertainty_csv(hw_counts_unc, output_dir / "hardware_counts_uncertainty.csv"))
    artifacts["simulator_expectation_uncertainty_csv"] = str(export_expectation_uncertainty_csv(sim_exp_unc, output_dir / "simulator_expectation_uncertainty.csv"))
    artifacts["hardware_expectation_uncertainty_csv"] = str(export_expectation_uncertainty_csv(hw_exp_unc, output_dir / "hardware_expectation_uncertainty.csv"))
    artifacts["simulator_counts_uncertainty_figure"] = str(plot_counts_uncertainty(sim_counts_unc, output_dir / "simulator_counts_uncertainty.png"))
    artifacts["hardware_counts_uncertainty_figure"] = str(plot_counts_uncertainty(hw_counts_unc, output_dir / "hardware_counts_uncertainty.png"))

    data.artifacts = artifacts
    artifacts["markdown_report"] = str(make_uncertainty_markdown_report(data, output_dir / "uncertainty_report.md"))
    artifacts["latex_report"] = str(make_uncertainty_latex_report(data, output_dir / "uncertainty_report.tex"))

    manifest = {
        "package": "AZM-QOS v2.6 uncertainty statistics",
        "n_bootstrap": n_bootstrap,
        "confidence_level": confidence_level,
        "simulator_expectation": sim_exp_unc.estimate,
        "hardware_expectation": hw_exp_unc.estimate,
        "difference": diff_unc.difference,
        "difference_ci": asdict(diff_unc.interval),
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "uncertainty_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)
    data.artifacts = artifacts
    return data
