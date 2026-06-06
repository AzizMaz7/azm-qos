from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import json
import csv
import math

@dataclass
class CountsComparisonResult:
    simulator_counts: dict[str, int]
    hardware_counts: dict[str, int]
    simulator_probabilities: dict[str, float]
    hardware_probabilities: dict[str, float]
    total_variation_distance: float
    shots_simulator: int
    shots_hardware: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "CountsComparisonResult\n"
            f"  shots_simulator: {self.shots_simulator}\n"
            f"  shots_hardware: {self.shots_hardware}\n"
            f"  total_variation_distance: {self.total_variation_distance:.8f}"
        )

@dataclass
class ExpectationComparisonResult:
    simulator_value: float
    hardware_value: float
    absolute_error: float
    relative_error: float | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "ExpectationComparisonResult\n"
            f"  simulator_value: {self.simulator_value:+.10f}\n"
            f"  hardware_value: {self.hardware_value:+.10f}\n"
            f"  absolute_error: {self.absolute_error:.8e}\n"
            f"  relative_error: {self.relative_error}"
        )

@dataclass
class BackendSnapshot:
    backend_name: str | None
    num_qubits: int | None
    basis_gates: list[str]
    coupling_map: Any | None
    backend_version: str | None = None
    properties_summary: dict[str, Any] = field(default_factory=dict)
    configuration_summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            "BackendSnapshot\n"
            f"  backend_name: {self.backend_name}\n"
            f"  num_qubits: {self.num_qubits}\n"
            f"  basis_gates: {self.basis_gates}\n"
            f"  backend_version: {self.backend_version}"
        )

@dataclass
class HardwareComparisonReportData:
    counts_comparison: CountsComparisonResult | None = None
    expectation_comparison: ExpectationComparisonResult | None = None
    backend_snapshot: BackendSnapshot | None = None
    job_metadata: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)

    def summary(self):
        lines = ["HardwareComparisonReportData"]
        if self.counts_comparison:
            lines.append(self.counts_comparison.summary())
        if self.expectation_comparison:
            lines.append(self.expectation_comparison.summary())
        if self.backend_snapshot:
            lines.append(self.backend_snapshot.summary())
        lines.append(f"  artifacts: {len(self.artifacts)}")
        return "\n".join(lines)

def normalize_counts(counts: dict[str, int | float]) -> dict[str, float]:
    total = float(sum(counts.values()))
    if total <= 0:
        return {str(k): 0.0 for k in counts}
    return {str(k): float(v) / total for k, v in counts.items()}

def total_variation_distance(p: dict[str, float], q: dict[str, float]) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(float(p.get(k, 0.0)) - float(q.get(k, 0.0))) for k in keys)

def compare_counts(simulator_counts, hardware_counts, **metadata) -> CountsComparisonResult:
    simulator_counts = {str(k): int(v) for k, v in dict(simulator_counts).items()}
    hardware_counts = {str(k): int(v) for k, v in dict(hardware_counts).items()}
    sim_probs = normalize_counts(simulator_counts)
    hw_probs = normalize_counts(hardware_counts)
    tvd = total_variation_distance(sim_probs, hw_probs)
    return CountsComparisonResult(
        simulator_counts=simulator_counts,
        hardware_counts=hardware_counts,
        simulator_probabilities=sim_probs,
        hardware_probabilities=hw_probs,
        total_variation_distance=tvd,
        shots_simulator=sum(simulator_counts.values()),
        shots_hardware=sum(hardware_counts.values()),
        metadata=metadata,
    )

def compare_expectation_values(simulator_value, hardware_value, **metadata) -> ExpectationComparisonResult:
    simulator_value = float(simulator_value)
    hardware_value = float(hardware_value)
    ae = abs(hardware_value - simulator_value)
    re = None if abs(simulator_value) < 1e-15 else ae / abs(simulator_value)
    return ExpectationComparisonResult(
        simulator_value=simulator_value,
        hardware_value=hardware_value,
        absolute_error=ae,
        relative_error=re,
        metadata=metadata,
    )

def parse_counts_from_runtime_result(result_payload):
    """Best-effort parser for counts-like Runtime/Aer results.

    Accepts:
    - direct dict of counts
    - object with get_counts()
    - dict with keys counts/quasi_dists/probabilities
    - Sampler-like nested data structures when possible
    """
    if result_payload is None:
        return {}

    if isinstance(result_payload, dict):
        if all(isinstance(v, (int, float)) for v in result_payload.values()):
            return {str(k): int(round(v)) for k, v in result_payload.items()}
        for key in ["counts", "quasi_dists", "probabilities"]:
            if key in result_payload:
                value = result_payload[key]
                if isinstance(value, list) and value:
                    value = value[0]
                if isinstance(value, dict):
                    # Convert probabilities/quasi distributions to pseudo-counts if needed.
                    if all(isinstance(v, float) and 0 <= v <= 1 for v in value.values()):
                        return {str(k): int(round(v * 10000)) for k, v in value.items()}
                    return {str(k): int(round(v)) for k, v in value.items()}

    if hasattr(result_payload, "get_counts"):
        counts = result_payload.get_counts()
        if isinstance(counts, list) and counts:
            counts = counts[0]
        return {str(k): int(v) for k, v in counts.items()}

    # Qiskit Runtime V2 result containers can vary by version.
    try:
        data = getattr(result_payload, "data", None)
        if data is not None:
            # Try classical register names.
            for name in ["meas", "c", "creg"]:
                reg = getattr(data, name, None)
                if reg is not None and hasattr(reg, "get_counts"):
                    return {str(k): int(v) for k, v in reg.get_counts().items()}
    except Exception:
        pass

    return {}

def parse_estimator_value(result_payload):
    """Best-effort parser for Estimator expectation values."""
    if result_payload is None:
        return None
    if isinstance(result_payload, (int, float)):
        return float(result_payload)
    if isinstance(result_payload, dict):
        for key in ["evs", "values", "value", "expectation", "mean"]:
            if key in result_payload:
                value = result_payload[key]
                if isinstance(value, list):
                    return float(value[0])
                return float(value)
    for attr in ["evs", "values", "value", "expectation", "mean"]:
        if hasattr(result_payload, attr):
            value = getattr(result_payload, attr)
            if isinstance(value, list):
                return float(value[0])
            try:
                return float(value)
            except Exception:
                pass
    try:
        if hasattr(result_payload, "__getitem__"):
            item = result_payload[0]
            return parse_estimator_value(item)
    except Exception:
        pass
    return None

def retrieve_ibm_job_result(job_id: str, config=None, timeout: float | None = None):
    """Retrieve an IBM Runtime job result when qiskit-ibm-runtime is available.

    This is safe to import without IBM packages; it raises a clear ImportError only when called.
    """
    try:
        from .ibm_runtime import construct_qiskit_runtime_service, IBMRuntimeConfig
    except Exception as exc:
        raise ImportError("AZM-QOS IBM Runtime helpers are unavailable.") from exc

    config = config or IBMRuntimeConfig()
    service = construct_qiskit_runtime_service(config)
    job = service.job(job_id)
    if timeout is None:
        return job.result()
    return job.result(timeout=timeout)

def backend_snapshot_from_backend(backend) -> BackendSnapshot:
    name = getattr(backend, "name", None)
    num_qubits = getattr(backend, "num_qubits", None)
    basis_gates = []
    coupling_map = None
    backend_version = None
    configuration_summary = {}
    properties_summary = {}

    try:
        config = backend.configuration()
        basis_gates = list(getattr(config, "basis_gates", []) or [])
        coupling_map = getattr(config, "coupling_map", None)
        backend_version = getattr(config, "backend_version", None)
        if num_qubits is None:
            num_qubits = getattr(config, "n_qubits", None)
        configuration_summary = {
            "backend_name": getattr(config, "backend_name", name),
            "n_qubits": getattr(config, "n_qubits", num_qubits),
            "simulator": getattr(config, "simulator", None),
            "basis_gates": basis_gates,
        }
    except Exception:
        pass

    try:
        props = backend.properties()
        properties_summary = {
            "last_update_date": str(getattr(props, "last_update_date", None)),
            "qubits": len(getattr(props, "qubits", []) or []),
            "gates": len(getattr(props, "gates", []) or []),
        }
    except Exception:
        pass

    return BackendSnapshot(
        backend_name=name,
        num_qubits=num_qubits,
        basis_gates=basis_gates,
        coupling_map=coupling_map,
        backend_version=backend_version,
        properties_summary=properties_summary,
        configuration_summary=configuration_summary,
    )

def save_backend_snapshot(snapshot: BackendSnapshot, path):
    path = Path(path)
    path.write_text(json.dumps(asdict(snapshot), indent=2, default=str), encoding="utf-8")
    return path

def save_counts_comparison_csv(comparison: CountsComparisonResult, path):
    path = Path(path)
    keys = sorted(set(comparison.simulator_probabilities) | set(comparison.hardware_probabilities))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["bitstring", "simulator_probability", "hardware_probability", "difference"])
        for k in keys:
            ps = comparison.simulator_probabilities.get(k, 0.0)
            ph = comparison.hardware_probabilities.get(k, 0.0)
            writer.writerow([k, ps, ph, ph - ps])
    return path

def plot_counts_comparison(comparison: CountsComparisonResult, path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text(comparison.summary(), encoding="utf-8")
        return txt

    keys = sorted(set(comparison.simulator_probabilities) | set(comparison.hardware_probabilities))
    x = list(range(len(keys)))
    sim = [comparison.simulator_probabilities.get(k, 0.0) for k in keys]
    hw = [comparison.hardware_probabilities.get(k, 0.0) for k in keys]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    width = 0.4
    ax.bar([i - width/2 for i in x], sim, width=width, label="simulator")
    ax.bar([i + width/2 for i in x], hw, width=width, label="hardware")
    ax.set_xticks(x)
    ax.set_xticklabels(keys, rotation=45, ha="right")
    ax.set_xlabel("bitstring")
    ax.set_ylabel("probability")
    ax.set_title("Hardware vs simulator counts")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path

def make_hardware_comparison_markdown_report(data: HardwareComparisonReportData, output_path):
    output_path = Path(output_path)
    lines = [
        "# AZM-QOS v2.4 Hardware-vs-Simulator Comparison Report",
        "",
        "## Summary",
        "",
        "```text",
        data.summary(),
        "```",
        "",
    ]

    if data.counts_comparison:
        lines.extend([
            "## Counts comparison",
            "",
            "```text",
            data.counts_comparison.summary(),
            "```",
            "",
        ])

    if data.expectation_comparison:
        lines.extend([
            "## Expectation-value comparison",
            "",
            "```text",
            data.expectation_comparison.summary(),
            "```",
            "",
        ])

    if data.backend_snapshot:
        lines.extend([
            "## Backend snapshot",
            "",
            "```text",
            data.backend_snapshot.summary(),
            "```",
            "",
        ])

    lines.extend([
        "## Job metadata",
        "",
        "```json",
        json.dumps(data.job_metadata, indent=2, default=str),
        "```",
        "",
        "## Artifacts",
        "",
    ])
    for key, value in data.artifacts.items():
        lines.append(f"- **{key}**: `{value}`")

    lines.extend([
        "",
        "## Scientific note",
        "",
        "Hardware comparisons should be interpreted together with backend calibration metadata, transpiled circuit depth, shot count, and mitigation settings.",
        "",
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path

def make_hardware_comparison_latex_report(data: HardwareComparisonReportData, output_path):
    output_path = Path(output_path)
    counts_summary = data.counts_comparison.summary() if data.counts_comparison else "No counts comparison."
    expectation_summary = data.expectation_comparison.summary() if data.expectation_comparison else "No expectation comparison."
    backend_summary = data.backend_snapshot.summary() if data.backend_snapshot else "No backend snapshot."

    tex = f"""
\\documentclass[11pt]{{article}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{booktabs}}
\\usepackage{{hyperref}}
\\title{{AZM-QOS v2.4 Hardware-vs-Simulator Comparison Report}}
\\author{{AZM-QOS Automated Research Workflow}}
\\date{{\\today}}
\\begin{{document}}
\\maketitle

\\section{{Counts Comparison}}
\\begin{{verbatim}}
{counts_summary}
\\end{{verbatim}}

\\section{{Expectation Comparison}}
\\begin{{verbatim}}
{expectation_summary}
\\end{{verbatim}}

\\section{{Backend Snapshot}}
\\begin{{verbatim}}
{backend_summary}
\\end{{verbatim}}

\\section{{Interpretation Note}}
Hardware comparisons should be interpreted together with backend calibration metadata, transpiled circuit depth, shot count, and mitigation settings.

\\end{{document}}
"""
    output_path.write_text(tex.strip() + "\n", encoding="utf-8")
    return output_path

def run_mock_hardware_comparison(output_dir, simulator_counts=None, hardware_counts=None):
    """Create a complete hardware-comparison artifact set from mock/saved counts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    simulator_counts = simulator_counts or {"00": 510, "11": 514}
    hardware_counts = hardware_counts or {"00": 470, "01": 30, "10": 34, "11": 490}

    counts_comparison = compare_counts(simulator_counts, hardware_counts, source="mock")
    expectation_comparison = compare_expectation_values(1.0, 0.91, source="mock")

    backend_snapshot = BackendSnapshot(
        backend_name="mock_ibm_backend",
        num_qubits=127,
        basis_gates=["rz", "sx", "x", "cx", "measure"],
        coupling_map=None,
        backend_version="mock",
        properties_summary={"note": "mock backend snapshot"},
    )

    data = HardwareComparisonReportData(
        counts_comparison=counts_comparison,
        expectation_comparison=expectation_comparison,
        backend_snapshot=backend_snapshot,
        job_metadata={"source": "mock_hardware_comparison"},
    )

    artifacts = {}
    artifacts["counts_comparison_csv"] = str(save_counts_comparison_csv(counts_comparison, output_dir / "counts_comparison.csv"))
    artifacts["counts_comparison_figure"] = str(plot_counts_comparison(counts_comparison, output_dir / "counts_comparison.png"))
    artifacts["backend_snapshot_json"] = str(save_backend_snapshot(backend_snapshot, output_dir / "backend_snapshot.json"))

    data.artifacts = artifacts
    artifacts["markdown_report"] = str(make_hardware_comparison_markdown_report(data, output_dir / "hardware_comparison_report.md"))
    artifacts["latex_report"] = str(make_hardware_comparison_latex_report(data, output_dir / "hardware_comparison_report.tex"))

    manifest = {
        "package": "AZM-QOS v2.4 hardware comparison",
        "artifacts": artifacts,
        "counts_tvd": counts_comparison.total_variation_distance,
        "expectation_absolute_error": expectation_comparison.absolute_error,
    }
    manifest_path = output_dir / "hardware_comparison_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    artifacts["manifest"] = str(manifest_path)

    data.artifacts = artifacts
    return data
