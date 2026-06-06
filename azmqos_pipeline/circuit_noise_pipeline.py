from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from azmqos_qec import repetition_code_3, build_syndrome_extraction_specs_for_code
from azmqos_qec.circuit_noise import CircuitNoiseModelSpec, circuit_noise_sweep
from azmqos_qec.qiskit_noise import (
    qiskit_aer_noise_available,
    run_noisy_syndrome_circuit_qiskit,
    estimate_noisy_syndrome_probability_scaffold,
)
from azmqos_qec.decoder_benchmarks import run_decoder_noise_sweep

@dataclass
class NoiseModelComparisonPoint:
    label: str
    two_qubit_error: float
    readout_error: float
    scaffold_syndrome_probability: float
    syndrome_bit_failure_rate: float
    qiskit_available: bool

@dataclass
class NoiseModelComparisonResult:
    points: list[NoiseModelComparisonPoint]
    metadata: dict

    def summary(self):
        lines = ["NoiseModelComparisonResult"]
        for p in self.points:
            lines.append(
                f"  {p.label}: p2={p.two_qubit_error:.4f}, readout={p.readout_error:.4f}, "
                f"scaffold_p1={p.scaffold_syndrome_probability:.6f}, "
                f"syndrome_failure={p.syndrome_bit_failure_rate:.6f}, "
                f"qiskit_available={p.qiskit_available}"
            )
        return "\n".join(lines)

def compare_circuit_noise_to_syndrome_noise(
    noise_specs=None,
    n_trials: int = 20,
    n_rounds: int = 5,
    shots: int = 256,
    seed: int | None = 123,
):
    """Compare circuit-noise scaffold estimates with syndrome-bit benchmark."""
    code = repetition_code_3()
    syndrome_specs = build_syndrome_extraction_specs_for_code(code)
    first_spec = syndrome_specs[0]
    stabilizer_weight = sum(1 for c in first_spec.stabilizer.pauli if c != "I")
    noise_specs = noise_specs or circuit_noise_sweep()

    points = []
    for spec in noise_specs:
        p_est = estimate_noisy_syndrome_probability_scaffold(spec, stabilizer_weight)
        bench = run_decoder_noise_sweep(
            code_spec=code,
            probabilities=[p_est],
            n_trials=n_trials,
            n_rounds=n_rounds,
            shots=shots,
            seed=seed,
        )
        failure = bench.points[0].failure_rate
        points.append(
            NoiseModelComparisonPoint(
                label=spec.label,
                two_qubit_error=spec.depolarizing.two_qubit_error,
                readout_error=0.5 * (spec.readout.p_1_given_0 + spec.readout.p_0_given_1),
                scaffold_syndrome_probability=p_est,
                syndrome_bit_failure_rate=failure,
                qiskit_available=qiskit_aer_noise_available(),
            )
        )

    return NoiseModelComparisonResult(
        points=points,
        metadata={
            "n_trials": n_trials,
            "n_rounds": n_rounds,
            "shots": shots,
            "qiskit_aer_noise_available": qiskit_aer_noise_available(),
        },
    )

def make_noise_model_comparison_report(result: NoiseModelComparisonResult, output_path=None):
    lines = [
        "# AZM-QOS v1.6 Noise Model Comparison Report",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "| label | two-qubit error | readout error | scaffold syndrome p(1) | decoder failure rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for p in result.points:
        lines.append(
            f"| {p.label} | {p.two_qubit_error:.6f} | {p.readout_error:.6f} | "
            f"{p.scaffold_syndrome_probability:.6f} | {p.syndrome_bit_failure_rate:.6f} |"
        )
    lines.extend([
        "",
        "## Note",
        "",
        "The circuit-level quantity is currently a scaffold estimate unless Qiskit Aer execution is explicitly used.",
    ])
    text = "\n".join(lines)
    if output_path is not None:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
