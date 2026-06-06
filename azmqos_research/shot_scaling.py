from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import csv
import math
import numpy as np

from azmqos import RuntimeManager, RuntimeConfig
from azmqos_endvqs import build_all_endvqs_workloads

@dataclass
class ShotScalingPoint:
    shots: int
    log2_shots: float
    estimate: float
    reference: float
    absolute_error: float
    log2_absolute_error: float
    repeats: int
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ShotScalingResult:
    workload_name: str
    observable_label: str
    points: list[ShotScalingPoint]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [
            f"ShotScalingResult(workload={self.workload_name}, observable={self.observable_label})",
            f"  points: {len(self.points)}",
        ]
        for p in self.points:
            lines.append(
                f"  shots={p.shots}, estimate={p.estimate:+.8f}, "
                f"AE={p.absolute_error:.6e}, log2(AE)={p.log2_absolute_error:.4f}"
            )
        return "\n".join(lines)

def _safe_log2(x, floor=1e-16):
    return math.log(max(abs(float(x)), floor), 2)

def run_single_workload_shot_scaling(
    workload,
    shot_powers=(6, 8, 10, 12),
    repeats: int = 20,
    seed: int | None = 123,
    backend_name: str = "shot_simulator",
):
    """Run shot-scaling for one END/VQS workload."""
    manager = RuntimeManager()
    reference_result = manager.run(workload, "local_statevector", RuntimeConfig())
    reference = float(np.real(reference_result.estimate_mean))

    points = []
    for power in shot_powers:
        shots = int(2 ** power)
        result = manager.run(
            workload,
            backend_name,
            RuntimeConfig(shots=shots, repeats=repeats, seed=None if seed is None else seed + power),
        )
        estimate = float(np.real(result.estimate_mean))
        ae = abs(estimate - reference)
        points.append(
            ShotScalingPoint(
                shots=shots,
                log2_shots=float(power),
                estimate=estimate,
                reference=reference,
                absolute_error=ae,
                log2_absolute_error=_safe_log2(ae),
                repeats=repeats,
                metadata={"backend_name": backend_name},
            )
        )

    return ShotScalingResult(
        workload_name=workload.name,
        observable_label=workload.name,
        points=points,
        metadata={"reference": reference, "backend_name": backend_name},
    )

def export_shot_scaling_csv(result: ShotScalingResult, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "workload_name", "shots", "log2_shots", "estimate", "reference",
            "absolute_error", "log2_absolute_error", "repeats"
        ])
        for p in result.points:
            writer.writerow([
                result.workload_name, p.shots, p.log2_shots, p.estimate,
                p.reference, p.absolute_error, p.log2_absolute_error, p.repeats
            ])
    return path

def plot_shot_scaling(result: ShotScalingResult, path):
    path = Path(path)
    try:
        import matplotlib.pyplot as plt
    except Exception:
        txt = path.with_suffix(".txt")
        txt.write_text(result.summary(), encoding="utf-8")
        return txt

    x = [p.log2_shots for p in result.points]
    y = [p.log2_absolute_error for p in result.points]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, y, marker="o")
    ax.set_xlabel("log2(number of shots)")
    ax.set_ylabel("log2(absolute error)")
    ax.set_title("Shot-scaling error")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=250)
    plt.close(fig)
    return path

def run_endvqs_shot_scaling_package(
    registry,
    output_dir,
    shot_powers=(6, 8, 10, 12),
    repeats: int = 20,
    seed: int | None = 123,
):
    """Run shot-scaling for the first END/VQS workload in a registry."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    workloads = build_all_endvqs_workloads(registry=registry)
    if not workloads:
        raise ValueError("No END/VQS workloads were generated.")

    result = run_single_workload_shot_scaling(
        workloads[0],
        shot_powers=shot_powers,
        repeats=repeats,
        seed=seed,
    )

    csv_path = export_shot_scaling_csv(result, output_dir / "shot_scaling.csv")
    fig_path = plot_shot_scaling(result, output_dir / "shot_scaling_loglog.png")

    return result, {"shot_scaling_csv": str(csv_path), "shot_scaling_figure": str(fig_path)}
