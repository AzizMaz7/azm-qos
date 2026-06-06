from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import csv

from .stabilizers import repetition_code_3
from .noise_models import QECNoiseModel, measurement_noise_sweep
from .decoder_execution import run_decoder_aware_qec_execution

@dataclass
class DecoderBenchmarkPoint:
    noise_model: QECNoiseModel
    n_trials: int
    n_failures: int
    failure_rate: float
    expected_correction: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"DecoderBenchmarkPoint(p_meas={self.noise_model.measurement_error_probability:.4f}, "
            f"trials={self.n_trials}, failures={self.n_failures}, "
            f"failure_rate={self.failure_rate:.6f})"
        )

@dataclass
class DecoderBenchmarkResult:
    code_name: str
    decoder_name: str
    n_rounds: int
    shots: int
    points: list[DecoderBenchmarkPoint]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [
            f"DecoderBenchmarkResult(code={self.code_name}, decoder={self.decoder_name}, rounds={self.n_rounds})",
            f"  shots per stabilizer workload: {self.shots}",
            "  points:",
        ]
        for p in self.points:
            lines.append(f"    {p.summary()}")
        threshold = estimate_pseudo_threshold(self)
        lines.append(f"  pseudo-threshold scaffold: {threshold}")
        return "\n".join(lines)

def run_decoder_noise_sweep(
    code_spec=None,
    probabilities=None,
    n_trials: int = 100,
    n_rounds: int = 5,
    shots: int = 1024,
    seed: int | None = 123,
    expected_correction: str = "I",
) -> DecoderBenchmarkResult:
    """Run repeated-syndrome decoder benchmark over measurement-error probabilities.

    Failure definition for this scaffold:
        no data error is intentionally inserted, so the correct correction is expected_correction.
        A trial fails if decoder_result.correction != expected_correction.
    """
    if n_trials <= 0:
        raise ValueError("n_trials must be positive.")

    code_spec = code_spec or repetition_code_3()
    noise_models = measurement_noise_sweep(probabilities)
    points = []

    for p_index, noise_model in enumerate(noise_models):
        noise_model.validate()
        failures = 0

        for trial in range(n_trials):
            trial_seed = None if seed is None else seed + 1000 * p_index + trial
            execution = run_decoder_aware_qec_execution(
                code_spec=code_spec,
                n_rounds=n_rounds,
                backend_name="local_statevector",
                shots=shots,
                seed=trial_seed,
                measurement_error_probability=noise_model.measurement_error_probability,
            )
            if execution.decoder_result.correction != expected_correction:
                failures += 1

        points.append(
            DecoderBenchmarkPoint(
                noise_model=noise_model,
                n_trials=n_trials,
                n_failures=failures,
                failure_rate=failures / n_trials,
                expected_correction=expected_correction,
                metadata={"failure_definition": "decoder_correction_mismatch"},
            )
        )

    return DecoderBenchmarkResult(
        code_name=code_spec.name,
        decoder_name="MajorityVoteRepetitionDecoder",
        n_rounds=n_rounds,
        shots=shots,
        points=points,
        metadata={"benchmark_type": "measurement_noise_sweep"},
    )

def estimate_pseudo_threshold(result: DecoderBenchmarkResult):
    """Approximate pseudo-threshold scaffold.

    Returns first measurement error p where observed failure_rate >= p.
    This is only a diagnostic scaffold, not a rigorous threshold estimate.
    """
    for point in result.points:
        p = point.noise_model.measurement_error_probability
        if point.failure_rate >= p and p > 0:
            return p
    return None

def export_decoder_benchmark_csv(result: DecoderBenchmarkResult, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "code_name",
            "decoder_name",
            "n_rounds",
            "shots",
            "measurement_error_probability",
            "n_trials",
            "n_failures",
            "failure_rate",
            "expected_correction",
        ])
        for point in result.points:
            writer.writerow([
                result.code_name,
                result.decoder_name,
                result.n_rounds,
                result.shots,
                point.noise_model.measurement_error_probability,
                point.n_trials,
                point.n_failures,
                point.failure_rate,
                point.expected_correction,
            ])
    return path

def make_decoder_benchmark_report(result: DecoderBenchmarkResult, output_path=None):
    lines = [
        "# AZM-QOS v1.5 Decoder Benchmark Report",
        "",
        "## Summary",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "## Table",
        "",
        "| measurement error | trials | failures | failure rate |",
        "|---:|---:|---:|---:|",
    ]

    for point in result.points:
        lines.append(
            f"| {point.noise_model.measurement_error_probability:.4f} | "
            f"{point.n_trials} | {point.n_failures} | {point.failure_rate:.6f} |"
        )

    lines.extend([
        "",
        "## Scientific note",
        "",
        "This benchmark injects measurement-bit flips into syndrome outcomes. It does not yet model full circuit-level noise or data-qubit error dynamics.",
        "",
    ])

    text = "\n".join(lines)
    if output_path is not None:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
