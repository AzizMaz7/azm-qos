from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import csv
import itertools
import numpy as np

from .hardware_compare import (
    CountsComparisonResult,
    ExpectationComparisonResult,
    HardwareComparisonReportData,
    BackendSnapshot,
    normalize_counts,
    compare_counts,
    compare_expectation_values,
    save_counts_comparison_csv,
    plot_counts_comparison,
)
try:
    from .ibm_results import retrieve_ibm_hardware_result
except Exception:
    retrieve_ibm_hardware_result = None


@dataclass
class ReadoutMitigationMatrix:
    """Single-qubit readout confusion matrix.

    Convention:
        observed_probability = matrix @ true_probability

    Rows are observed labels, columns are true labels:
        [[P(obs=0|true=0), P(obs=0|true=1)],
         [P(obs=1|true=0), P(obs=1|true=1)]]
    """
    matrix: list[list[float]]
    qubit: int | None = None
    label: str = "readout_mitigation_matrix"
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_array(self):
        arr = np.asarray(self.matrix, dtype=float)
        if arr.shape != (2, 2):
            raise ValueError("Readout mitigation matrix must be 2x2.")
        return arr

    def inverse(self):
        return np.linalg.pinv(self.as_array())

    def summary(self):
        return f"ReadoutMitigationMatrix(qubit={self.qubit}, matrix={self.matrix})"


@dataclass
class CalibrationSnapshot:
    backend_name: str
    timestamp: str | None = None
    readout_error: float | None = None
    one_qubit_error: float | None = None
    two_qubit_error: float | None = None
    t1_median_us: float | None = None
    t2_median_us: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "CalibrationSnapshot\n"
            f"  backend_name: {self.backend_name}\n"
            f"  timestamp: {self.timestamp}\n"
            f"  readout_error: {self.readout_error}\n"
            f"  one_qubit_error: {self.one_qubit_error}\n"
            f"  two_qubit_error: {self.two_qubit_error}\n"
            f"  t1_median_us: {self.t1_median_us}\n"
            f"  t2_median_us: {self.t2_median_us}"
        )


@dataclass
class MitigatedCountsResult:
    raw_counts: dict[str, int]
    raw_probabilities: dict[str, float]
    mitigated_probabilities: dict[str, float]
    mitigation_matrices: list[ReadoutMitigationMatrix]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "MitigatedCountsResult\n"
            f"  bitstrings: {len(self.mitigated_probabilities)}\n"
            f"  matrices: {len(self.mitigation_matrices)}"
        )


@dataclass
class ZNEResult:
    noise_scales: list[float]
    values: list[float]
    extrapolated_zero_noise_value: float
    fit_order: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "ZNEResult\n"
            f"  fit_order: {self.fit_order}\n"
            f"  zero_noise_value: {self.extrapolated_zero_noise_value:+.10f}\n"
            f"  points: {list(zip(self.noise_scales, self.values))}"
        )


@dataclass
class MitigationReportData:
    calibration_snapshot: CalibrationSnapshot
    mitigated_counts_result: MitigatedCountsResult | None = None
    raw_counts_comparison: CountsComparisonResult | None = None
    mitigated_counts_comparison: CountsComparisonResult | None = None
    zne_result: ZNEResult | None = None
    expectation_comparison: ExpectationComparisonResult | None = None
    job_metadata: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)

    def summary(self):
        lines = ["MitigationReportData", self.calibration_snapshot.summary()]
        if self.raw_counts_comparison:
            lines.append("Raw counts:")
            lines.append(self.raw_counts_comparison.summary())
        if self.mitigated_counts_comparison:
            lines.append("Mitigated counts:")
            lines.append(self.mitigated_counts_comparison.summary())
        if self.zne_result:
            lines.append(self.zne_result.summary())
        return "\n".join(lines)


def readout_matrix_from_error(error_probability: float, qubit: int | None = None):
    p = float(error_probability)
    if not (0.0 <= p <= 1.0):
        raise ValueError("error_probability must be between 0 and 1.")
    return ReadoutMitigationMatrix(
        matrix=[[1.0 - p, p], [p, 1.0 - p]],
        qubit=qubit,
        metadata={"source": "symmetric_error_probability", "error_probability": p},
    )


def readout_matrices_from_calibration(calibration: CalibrationSnapshot, n_qubits: int):
    p = calibration.readout_error if calibration.readout_error is not None else 0.02
    return [readout_matrix_from_error(p, qubit=i) for i in range(n_qubits)]


def _all_bitstrings(n_qubits: int):
    return ["".join(bits) for bits in itertools.product("01", repeat=n_qubits)]


def _counts_to_probability_vector(counts: dict[str, int], bitstrings: list[str]):
    probs = normalize_counts(counts)
    return np.asarray([probs.get(b, 0.0) for b in bitstrings], dtype=float)


def _probability_vector_to_dict(vector, bitstrings):
    return {b: float(vector[i]) for i, b in enumerate(bitstrings)}


def _tensor_confusion_matrix(matrices: list[ReadoutMitigationMatrix]):
    arr = matrices[0].as_array()
    for m in matrices[1:]:
        arr = np.kron(arr, m.as_array())
    return arr


def project_to_probability_simple(vector):
    vector = np.asarray(vector, dtype=float)
    vector = np.maximum(vector, 0.0)
    total = float(vector.sum())
    if total <= 0:
        return np.ones_like(vector) / len(vector)
    return vector / total


def mitigate_counts_readout(counts: dict[str, int], matrices: list[ReadoutMitigationMatrix]) -> MitigatedCountsResult:
    if not counts:
        raise ValueError("counts cannot be empty.")
    n_qubits = max(len(str(k).replace(" ", "")) for k in counts.keys())
    if len(matrices) != n_qubits:
        raise ValueError(f"Expected {n_qubits} readout matrices, got {len(matrices)}.")

    cleaned_counts = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}
    bitstrings = _all_bitstrings(n_qubits)
    observed = _counts_to_probability_vector(cleaned_counts, bitstrings)
    confusion = _tensor_confusion_matrix(matrices)
    mitigated = np.linalg.pinv(confusion) @ observed
    mitigated = project_to_probability_simple(mitigated)

    return MitigatedCountsResult(
        raw_counts=cleaned_counts,
        raw_probabilities=_probability_vector_to_dict(observed, bitstrings),
        mitigated_probabilities=_probability_vector_to_dict(mitigated, bitstrings),
        mitigation_matrices=matrices,
        metadata={"n_qubits": n_qubits},
    )


def mitigated_probabilities_to_pseudo_counts(mitigated_probabilities: dict[str, float], shots: int):
    return {k: int(round(float(v) * shots)) for k, v in mitigated_probabilities.items()}


def zero_noise_extrapolate(noise_scales, values, fit_order: int = 1) -> ZNEResult:
    noise_scales = [float(x) for x in noise_scales]
    values = [float(v) for v in values]
    if len(noise_scales) != len(values):
        raise ValueError("noise_scales and values must have the same length.")
    if len(values) < fit_order + 1:
        raise ValueError("Need at least fit_order + 1 data points.")

    coeffs = np.polyfit(noise_scales, values, deg=fit_order)
    extrapolated = float(np.polyval(coeffs, 0.0))
    return ZNEResult(
        noise_scales=noise_scales,
        values=values,
        extrapolated_zero_noise_value=extrapolated,
        fit_order=fit_order,
        metadata={"polyfit_coefficients": [float(c) for c in coeffs]},
    )


def calibration_snapshot_from_backend_snapshot(backend_snapshot: BackendSnapshot) -> CalibrationSnapshot:
    props = backend_snapshot.properties_summary or {}
    cfg = backend_snapshot.configuration_summary or {}
    return CalibrationSnapshot(
        backend_name=backend_snapshot.backend_name or cfg.get("backend_name") or "unknown_backend",
        timestamp=props.get("last_update_date"),
        readout_error=props.get("readout_error_median", props.get("readout_error")),
        one_qubit_error=props.get("one_qubit_error"),
        two_qubit_error=props.get("two_qubit_error"),
        t1_median_us=props.get("t1_median_us"),
        t2_median_us=props.get("t2_median_us"),
        metadata={"source": "backend_snapshot"},
    )


def mock_calibration_snapshot():
    return CalibrationSnapshot(
        backend_name="mock_ibm_backend",
        timestamp="mock_timestamp",
        readout_error=0.03,
        one_qubit_error=0.001,
        two_qubit_error=0.01,
        t1_median_us=150.0,
        t2_median_us=100.0,
        metadata={"source": "mock"},
    )


def save_calibration_snapshot(snapshot: CalibrationSnapshot, path):
    path = Path(path)
    path.write_text(json.dumps(asdict(snapshot), indent=2, default=str), encoding="utf-8")
    return path


def save_mitigated_probabilities_csv(result: MitigatedCountsResult, path):
    path = Path(path)
    keys = sorted(set(result.raw_probabilities) | set(result.mitigated_probabilities))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bitstring", "raw_probability", "mitigated_probability"])
        for k in keys:
            writer.writerow([k, result.raw_probabilities.get(k, 0.0), result.mitigated_probabilities.get(k, 0.0)])
    return path


def plot_mitigated_probabilities(result: MitigatedCountsResult, path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text(result.summary(), encoding="utf-8")
        return txt

    keys = sorted(set(result.raw_probabilities) | set(result.mitigated_probabilities))
    x = list(range(len(keys)))
    raw = [result.raw_probabilities.get(k, 0.0) for k in keys]
    mit = [result.mitigated_probabilities.get(k, 0.0) for k in keys]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    width = 0.4
    ax.bar([i - width / 2 for i in x], raw, width=width, label="raw")
    ax.bar([i + width / 2 for i in x], mit, width=width, label="mitigated")
    ax.set_xticks(x)
    ax.set_xticklabels(keys, rotation=45, ha="right")
    ax.set_xlabel("bitstring")
    ax.set_ylabel("probability")
    ax.set_title("Readout mitigation")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def plot_zne(result: ZNEResult, path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text(result.summary(), encoding="utf-8")
        return txt

    x = result.noise_scales
    y = result.values
    coeffs = result.metadata.get("polyfit_coefficients", [])
    xs = np.linspace(0.0, max(x), 100)
    ys = np.polyval(coeffs, xs) if coeffs else np.zeros_like(xs)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, y, marker="o", linestyle="", label="measured")
    ax.plot(xs, ys, label="fit")
    ax.axvline(0.0, linestyle="--")
    ax.set_xlabel("noise scale")
    ax.set_ylabel("expectation value")
    ax.set_title("Zero-noise extrapolation")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path


def make_mitigation_markdown_report(data: MitigationReportData, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v2.5 Calibration-Aware Mitigation Report",
        "",
        "## Summary",
        "",
        "```text",
        data.summary(),
        "```",
        "",
        "## Calibration snapshot",
        "",
        "```text",
        data.calibration_snapshot.summary(),
        "```",
        "",
    ]

    if data.raw_counts_comparison:
        lines.extend(["## Raw counts comparison", "", "```text", data.raw_counts_comparison.summary(), "```", ""])
    if data.mitigated_counts_comparison:
        lines.extend(["## Mitigated counts comparison", "", "```text", data.mitigated_counts_comparison.summary(), "```", ""])
    if data.zne_result:
        lines.extend(["## Zero-noise extrapolation", "", "```text", data.zne_result.summary(), "```", ""])

    lines.extend(["## Job metadata", "", "```json", json.dumps(data.job_metadata, indent=2, default=str), "```", ""])
    lines.extend(["## Artifacts", ""])
    for key, value in data.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")

    lines.extend([
        "",
        "## Scientific note",
        "",
        "This report uses scaffold mitigation methods. For publication, validate mitigation assumptions using calibration data, control circuits, and uncertainty analysis.",
        "",
    ])
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def make_mitigation_latex_report(data: MitigationReportData, output_path):
    output_path = Path(output_path)
    raw = data.raw_counts_comparison.summary() if data.raw_counts_comparison else "No raw comparison."
    mit = data.mitigated_counts_comparison.summary() if data.mitigated_counts_comparison else "No mitigated comparison."
    zne = data.zne_result.summary() if data.zne_result else "No ZNE result."

    tex = f"""
\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{booktabs}}
\\title{{AZM-QOS v2.5 Calibration-Aware Mitigation Report}}
\\author{{AZM-QOS Automated Research Workflow}}
\\date{{\\today}}
\\begin{{document}}
\\maketitle

\\section{{Calibration Snapshot}}
\\begin{{verbatim}}
{data.calibration_snapshot.summary()}
\\end{{verbatim}}

\\section{{Raw Counts Comparison}}
\\begin{{verbatim}}
{raw}
\\end{{verbatim}}

\\section{{Mitigated Counts Comparison}}
\\begin{{verbatim}}
{mit}
\\end{{verbatim}}

\\section{{Zero-Noise Extrapolation}}
\\begin{{verbatim}}
{zne}
\\end{{verbatim}}

\\section{{Limitations}}
This report uses scaffold mitigation methods. For publication, validate mitigation assumptions using calibration data, control circuits, and uncertainty analysis.

\\end{{document}}
"""
    output_path.write_text(tex.strip() + "\n", encoding="utf-8")
    return output_path


def run_mitigation_workflow_from_counts(
    output_dir,
    simulator_counts: dict[str, int],
    hardware_counts: dict[str, int],
    calibration: CalibrationSnapshot | None = None,
    zne_noise_scales=None,
    zne_values=None,
    job_metadata=None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    calibration = calibration or mock_calibration_snapshot()
    n_qubits = max(len(str(k).replace(" ", "")) for k in hardware_counts.keys())
    matrices = readout_matrices_from_calibration(calibration, n_qubits=n_qubits)
    mitigated = mitigate_counts_readout(hardware_counts, matrices)
    mitigated_pseudo_counts = mitigated_probabilities_to_pseudo_counts(
        mitigated.mitigated_probabilities,
        sum(hardware_counts.values()),
    )

    raw_comparison = compare_counts(simulator_counts, hardware_counts, source="raw")
    mitigated_comparison = compare_counts(simulator_counts, mitigated_pseudo_counts, source="mitigated")

    zne_noise_scales = zne_noise_scales or [1.0, 2.0, 3.0]
    zne_values = zne_values or [0.91, 0.84, 0.76]
    zne = zero_noise_extrapolate(zne_noise_scales, zne_values, fit_order=1)
    expectation = compare_expectation_values(1.0, zne.extrapolated_zero_noise_value, source="zne")

    data = MitigationReportData(
        calibration_snapshot=calibration,
        mitigated_counts_result=mitigated,
        raw_counts_comparison=raw_comparison,
        mitigated_counts_comparison=mitigated_comparison,
        zne_result=zne,
        expectation_comparison=expectation,
        job_metadata=job_metadata or {},
        artifacts={},
    )

    artifacts = {}
    artifacts["calibration_snapshot_json"] = str(save_calibration_snapshot(calibration, output_dir / "calibration_snapshot.json"))
    artifacts["mitigated_probabilities_csv"] = str(save_mitigated_probabilities_csv(mitigated, output_dir / "mitigated_probabilities.csv"))
    artifacts["mitigated_probabilities_figure"] = str(plot_mitigated_probabilities(mitigated, output_dir / "mitigated_probabilities.png"))
    artifacts["raw_counts_comparison_csv"] = str(save_counts_comparison_csv(raw_comparison, output_dir / "raw_counts_comparison.csv"))
    artifacts["mitigated_counts_comparison_csv"] = str(save_counts_comparison_csv(mitigated_comparison, output_dir / "mitigated_counts_comparison.csv"))
    artifacts["raw_counts_comparison_figure"] = str(plot_counts_comparison(raw_comparison, output_dir / "raw_counts_comparison.png"))
    artifacts["mitigated_counts_comparison_figure"] = str(plot_counts_comparison(mitigated_comparison, output_dir / "mitigated_counts_comparison.png"))
    artifacts["zne_figure"] = str(plot_zne(zne, output_dir / "zero_noise_extrapolation.png"))

    data.artifacts = artifacts
    artifacts["markdown_report"] = str(make_mitigation_markdown_report(data, output_dir / "mitigation_report.md"))
    artifacts["latex_report"] = str(make_mitigation_latex_report(data, output_dir / "mitigation_report.tex"))

    manifest = {
        "package": "AZM-QOS v2.5 calibration-aware mitigation",
        "raw_tvd": raw_comparison.total_variation_distance,
        "mitigated_tvd": mitigated_comparison.total_variation_distance,
        "zne_zero_noise_value": zne.extrapolated_zero_noise_value,
        "job_metadata": data.job_metadata,
        "artifacts": artifacts,
    }
    manifest_path = output_dir / "mitigation_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)
    data.artifacts = artifacts
    return data


def run_mock_mitigation_workflow(output_dir, simulator_counts=None, hardware_counts=None):
    simulator_counts = simulator_counts or {"00": 510, "11": 514}
    hardware_counts = hardware_counts or {"00": 470, "01": 30, "10": 34, "11": 490}
    return run_mitigation_workflow_from_counts(
        output_dir=output_dir,
        simulator_counts=simulator_counts,
        hardware_counts=hardware_counts,
        calibration=mock_calibration_snapshot(),
        job_metadata={"source": "mock_hardware_comparison"},
    )


def run_latest_hardware_mitigation_workflow(
    output_dir,
    simulator_counts: dict[str, int],
    backend_name: str | None = None,
    job_id: str | None = None,
    calibration: CalibrationSnapshot | None = None,
):
    """Retrieve the latest/exact IBM job counts and run mitigation.

    backend_name=None means latest visible job from any backend.
    """
    if retrieve_ibm_hardware_result is None:
        raise ImportError("ibm_results helper is unavailable.")

    hardware = retrieve_ibm_hardware_result(job_id=job_id, backend_name=backend_name)
    if hardware.counts is None:
        raise RuntimeError("No hardware counts were extracted from the IBM Runtime result.")

    calibration = calibration or CalibrationSnapshot(
        backend_name=hardware.backend_name or "unknown_backend",
        readout_error=0.03,
        metadata={"source": "default_from_hardware_job"},
    )

    return run_mitigation_workflow_from_counts(
        output_dir=output_dir,
        simulator_counts=simulator_counts,
        hardware_counts=hardware.counts,
        calibration=calibration,
        job_metadata={
            "job_id": hardware.job_id,
            "backend_name": hardware.backend_name,
            "status": hardware.status,
        },
    )
