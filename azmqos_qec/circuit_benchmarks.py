from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import csv
import numpy as np

from .stabilizers import repetition_code_3
from .syndrome_circuits import build_syndrome_extraction_specs_for_code
from .circuit_noise import CircuitNoiseModelSpec, circuit_noise_sweep, default_circuit_noise_spec
from .qiskit_noise import (
    qiskit_aer_noise_available,
    run_noisy_syndrome_circuit_qiskit,
    estimate_noisy_syndrome_probability_scaffold,
)
from .syndromes import SyndromeResult
from .decoders import MajorityVoteRepetitionDecoder

@dataclass
class CircuitSyndromeRoundRecord:
    """One repeated circuit-level syndrome round.

    Each stabilizer produces one syndrome bit. In scaffold mode, the syndrome bit
    is sampled from a probability estimated from the circuit-noise spec. In Qiskit
    mode, it is extracted from noisy syndrome-circuit counts.
    """

    round_index: int
    syndrome_bits: dict[str, int]
    syndrome_probabilities: dict[str, float]
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [f"CircuitSyndromeRoundRecord(round={self.round_index})"]
        for name, bit in self.syndrome_bits.items():
            p = self.syndrome_probabilities.get(name, 0.0)
            lines.append(f"  {name}: bit={bit}, p1={p:.6f}")
        return "\n".join(lines)

@dataclass
class CircuitLevelSyndromeBenchmarkResult:
    code_name: str
    noise_spec: CircuitNoiseModelSpec
    rounds: list[CircuitSyndromeRoundRecord]
    majority_syndrome_bits: dict[str, int]
    decoder_correction: str
    decoder_confidence: float
    used_qiskit: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_rounds(self):
        return len(self.rounds)

    def summary(self):
        lines = [
            f"CircuitLevelSyndromeBenchmarkResult(code={self.code_name}, rounds={self.n_rounds})",
            f"  noise: {self.noise_spec.label}",
            f"  used_qiskit: {self.used_qiskit}",
            f"  majority_syndrome: {self.majority_syndrome_bits}",
            f"  decoder_correction: {self.decoder_correction}",
            f"  decoder_confidence: {self.decoder_confidence:.3f}",
        ]
        return "\n".join(lines)

@dataclass
class CircuitLevelDecoderSweepPoint:
    noise_label: str
    two_qubit_error: float
    readout_error: float
    n_trials: int
    n_failures: int
    failure_rate: float
    used_qiskit: bool

    def summary(self):
        return (
            f"CircuitLevelDecoderSweepPoint(label={self.noise_label}, "
            f"p2={self.two_qubit_error:.6f}, readout={self.readout_error:.6f}, "
            f"trials={self.n_trials}, failures={self.n_failures}, "
            f"failure_rate={self.failure_rate:.6f}, qiskit={self.used_qiskit})"
        )

@dataclass
class CircuitLevelDecoderSweepResult:
    code_name: str
    n_rounds: int
    shots: int
    points: list[CircuitLevelDecoderSweepPoint]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [
            f"CircuitLevelDecoderSweepResult(code={self.code_name}, rounds={self.n_rounds}, shots={self.shots})"
        ]
        for p in self.points:
            lines.append(f"  {p.summary()}")
        return "\n".join(lines)

def counts_to_syndrome_bit(counts: dict[str, int]) -> int:
    """Extract syndrome bit by majority vote from one-bit measurement counts.

    If counts contain multi-bit keys, this uses the rightmost bit, matching the
    simple one-classical-bit syndrome-circuit convention used in the scaffold.
    """
    zeros = 0
    ones = 0
    for bitstring, count in counts.items():
        bit = bitstring.replace(" ", "")[-1]
        if bit == "1":
            ones += count
        else:
            zeros += count
    return 1 if ones > zeros else 0

def majority_vote_rounds(rounds: list[CircuitSyndromeRoundRecord]) -> dict[str, int]:
    if not rounds:
        return {}
    names = list(rounds[0].syndrome_bits.keys())
    out = {}
    for name in names:
        values = [r.syndrome_bits.get(name, 0) for r in rounds]
        out[name] = 1 if sum(values) > len(values) / 2 else 0
    return out

def _syndrome_result_from_majority(code_name: str, majority_bits: dict[str, int]) -> SyndromeResult:
    return SyndromeResult(
        code_name=code_name,
        stabilizer_values={name: (+1.0 if bit == 0 else -1.0) for name, bit in majority_bits.items()},
        syndrome_bits=dict(majority_bits),
        metadata={"source": "circuit_level_majority_vote"},
    )

def _sample_bit_from_probability(probability: float, rng) -> int:
    return 1 if rng.random() < probability else 0

def run_circuit_level_syndrome_benchmark(
    code_spec=None,
    noise_spec: CircuitNoiseModelSpec | None = None,
    n_rounds: int = 5,
    shots: int = 1024,
    seed: int | None = 123,
    use_qiskit_if_available: bool = False,
):
    """Run repeated syndrome rounds using circuit-level noise scaffolding.

    If Qiskit Aer is available and use_qiskit_if_available=True, this can run
    noisy syndrome circuits. Otherwise, it uses a scaffold probability model.
    """
    if n_rounds <= 0:
        raise ValueError("n_rounds must be positive.")
    code_spec = code_spec or repetition_code_3()
    noise_spec = noise_spec or default_circuit_noise_spec()
    noise_spec.validate()
    rng = np.random.default_rng(seed)

    syndrome_specs = build_syndrome_extraction_specs_for_code(code_spec)
    use_qiskit = bool(use_qiskit_if_available and qiskit_aer_noise_available())

    records = []
    for r in range(n_rounds):
        bits = {}
        probabilities = {}
        counts_by_stabilizer = {}

        for spec in syndrome_specs:
            weight = sum(1 for c in spec.stabilizer.pauli if c != "I")

            if use_qiskit:
                try:
                    qres = run_noisy_syndrome_circuit_qiskit(
                        spec,
                        noise_spec,
                        shots=shots,
                        seed=None if seed is None else seed + r,
                    )
                    bit = counts_to_syndrome_bit(qres.counts)
                    p1 = qres.syndrome_probability_1
                    counts_by_stabilizer[spec.stabilizer.name] = qres.counts
                except Exception:
                    p1 = estimate_noisy_syndrome_probability_scaffold(noise_spec, weight)
                    bit = _sample_bit_from_probability(p1, rng)
            else:
                p1 = estimate_noisy_syndrome_probability_scaffold(noise_spec, weight)
                bit = _sample_bit_from_probability(p1, rng)

            bits[spec.stabilizer.name] = bit
            probabilities[spec.stabilizer.name] = p1

        records.append(
            CircuitSyndromeRoundRecord(
                round_index=r,
                syndrome_bits=bits,
                syndrome_probabilities=probabilities,
                counts=counts_by_stabilizer,
                metadata={"shots": shots, "use_qiskit": use_qiskit},
            )
        )

    majority = majority_vote_rounds(records)
    syndrome = _syndrome_result_from_majority(code_spec.name, majority)
    decoder_result = MajorityVoteRepetitionDecoder().decode(syndrome)

    return CircuitLevelSyndromeBenchmarkResult(
        code_name=code_spec.name,
        noise_spec=noise_spec,
        rounds=records,
        majority_syndrome_bits=majority,
        decoder_correction=decoder_result.correction,
        decoder_confidence=decoder_result.confidence,
        used_qiskit=use_qiskit,
        metadata={"shots": shots, "seed": seed},
    )

def run_circuit_level_decoder_sweep(
    code_spec=None,
    noise_specs=None,
    n_trials: int = 50,
    n_rounds: int = 5,
    shots: int = 1024,
    seed: int | None = 123,
    expected_correction: str = "I",
    use_qiskit_if_available: bool = False,
):
    """Sweep circuit-noise specs and estimate decoder failure rate."""
    if n_trials <= 0:
        raise ValueError("n_trials must be positive.")
    code_spec = code_spec or repetition_code_3()
    noise_specs = noise_specs or circuit_noise_sweep()

    points = []
    for noise_index, noise_spec in enumerate(noise_specs):
        failures = 0
        used_qiskit_any = False

        for trial in range(n_trials):
            trial_seed = None if seed is None else seed + 1000 * noise_index + trial
            result = run_circuit_level_syndrome_benchmark(
                code_spec=code_spec,
                noise_spec=noise_spec,
                n_rounds=n_rounds,
                shots=shots,
                seed=trial_seed,
                use_qiskit_if_available=use_qiskit_if_available,
            )
            used_qiskit_any = used_qiskit_any or result.used_qiskit
            if result.decoder_correction != expected_correction:
                failures += 1

        readout_error = 0.5 * (noise_spec.readout.p_1_given_0 + noise_spec.readout.p_0_given_1)
        points.append(
            CircuitLevelDecoderSweepPoint(
                noise_label=noise_spec.label,
                two_qubit_error=noise_spec.depolarizing.two_qubit_error,
                readout_error=readout_error,
                n_trials=n_trials,
                n_failures=failures,
                failure_rate=failures / n_trials,
                used_qiskit=used_qiskit_any,
            )
        )

    return CircuitLevelDecoderSweepResult(
        code_name=code_spec.name,
        n_rounds=n_rounds,
        shots=shots,
        points=points,
        metadata={"expected_correction": expected_correction},
    )

def export_circuit_level_decoder_sweep_csv(result: CircuitLevelDecoderSweepResult, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "code_name",
            "n_rounds",
            "shots",
            "noise_label",
            "two_qubit_error",
            "readout_error",
            "n_trials",
            "n_failures",
            "failure_rate",
            "used_qiskit",
        ])
        for p in result.points:
            writer.writerow([
                result.code_name,
                result.n_rounds,
                result.shots,
                p.noise_label,
                p.two_qubit_error,
                p.readout_error,
                p.n_trials,
                p.n_failures,
                p.failure_rate,
                p.used_qiskit,
            ])
    return path

def make_circuit_level_decoder_sweep_report(result: CircuitLevelDecoderSweepResult, output_path=None):
    lines = [
        "# AZM-QOS v1.7 Circuit-Level Decoder Sweep Report",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "| noise label | two-qubit error | readout error | trials | failures | failure rate | Qiskit used |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for p in result.points:
        lines.append(
            f"| {p.noise_label} | {p.two_qubit_error:.6f} | {p.readout_error:.6f} | "
            f"{p.n_trials} | {p.n_failures} | {p.failure_rate:.6f} | {p.used_qiskit} |"
        )
    lines.extend([
        "",
        "## Note",
        "",
        "This v1.7 benchmark can use Qiskit Aer if installed, but otherwise uses a circuit-noise scaffold probability model.",
    ])
    text = "\n".join(lines)
    if output_path is not None:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
