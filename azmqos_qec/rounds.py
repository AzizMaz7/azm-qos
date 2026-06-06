from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np

from azmqos import RuntimeManager, RuntimeConfig
from .builders import build_stabilizer_workloads
from .syndromes import infer_syndrome_from_stabilizers, SyndromeResult

@dataclass
class SyndromeRoundRecord:
    """One round of stabilizer-syndrome measurement."""

    round_index: int
    stabilizer_values: dict[str, float]
    syndrome_bits: dict[str, int]
    raw_syndrome_bits: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [f"SyndromeRoundRecord(round={self.round_index})"]
        for name, bit in self.syndrome_bits.items():
            raw = self.raw_syndrome_bits.get(name, bit)
            val = self.stabilizer_values.get(name, 0.0)
            lines.append(f"  {name}: value={val:+.6f}, raw={raw}, final={bit}")
        return "\n".join(lines)

@dataclass
class RepeatedSyndromeResult:
    """Repeated syndrome measurement result."""

    code_name: str
    rounds: list[SyndromeRoundRecord]
    majority_syndrome_bits: dict[str, int]
    measurement_error_probability: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_rounds(self):
        return len(self.rounds)

    def summary(self):
        lines = [
            f"RepeatedSyndromeResult(code={self.code_name}, rounds={self.n_rounds})",
            f"  measurement_error_probability: {self.measurement_error_probability}",
            "  majority syndrome:",
        ]
        for name, bit in self.majority_syndrome_bits.items():
            lines.append(f"    {name}: {bit}")
        return "\n".join(lines)

def _maybe_flip_bit(bit: int, probability: float, rng) -> int:
    if probability <= 0:
        return bit
    return 1 - bit if rng.random() < probability else bit

def majority_vote_syndrome(rounds: list[SyndromeRoundRecord]) -> dict[str, int]:
    """Take majority vote over repeated syndrome bits."""
    if not rounds:
        return {}
    names = list(rounds[0].syndrome_bits.keys())
    majority = {}
    for name in names:
        values = [r.syndrome_bits.get(name, 0) for r in rounds]
        ones = sum(values)
        zeros = len(values) - ones
        majority[name] = 1 if ones > zeros else 0
    return majority

def run_repeated_syndrome_rounds(
    code_spec,
    n_rounds: int = 3,
    backend_name: str = "local_statevector",
    shots: int = 4096,
    seed: int | None = 123,
    measurement_error_probability: float = 0.0,
):
    """Run repeated stabilizer syndrome rounds.

    This function executes stabilizer workloads and optionally flips syndrome bits
    to simulate measurement error. It does not yet model data-qubit error dynamics.
    """
    if n_rounds <= 0:
        raise ValueError("n_rounds must be positive.")
    if not (0.0 <= measurement_error_probability <= 1.0):
        raise ValueError("measurement_error_probability must be between 0 and 1.")

    rng = np.random.default_rng(seed)
    manager = RuntimeManager()
    workloads = build_stabilizer_workloads(code_spec)
    records = []

    for round_index in range(n_rounds):
        results = []
        for workload in workloads:
            round_seed = None if seed is None else seed + round_index
            result = manager.run(
                workload,
                backend_name,
                RuntimeConfig(shots=shots, repeats=1, seed=round_seed),
            )
            results.append(result)

        syndrome = infer_syndrome_from_stabilizers(results)
        raw_bits = dict(syndrome.syndrome_bits)
        final_bits = {
            name: _maybe_flip_bit(bit, measurement_error_probability, rng)
            for name, bit in raw_bits.items()
        }

        records.append(
            SyndromeRoundRecord(
                round_index=round_index,
                stabilizer_values=dict(syndrome.stabilizer_values),
                syndrome_bits=final_bits,
                raw_syndrome_bits=raw_bits,
                metadata={
                    "backend_name": backend_name,
                    "shots": shots,
                    "measurement_error_probability": measurement_error_probability,
                },
            )
        )

    return RepeatedSyndromeResult(
        code_name=code_spec.name,
        rounds=records,
        majority_syndrome_bits=majority_vote_syndrome(records),
        measurement_error_probability=measurement_error_probability,
        metadata={"backend_name": backend_name, "shots": shots, "seed": seed},
    )

def repeated_syndrome_to_syndrome_result(repeated_result: RepeatedSyndromeResult) -> SyndromeResult:
    """Convert majority syndrome bits into a SyndromeResult for decoder interfaces."""
    values = {}
    for name, bit in repeated_result.majority_syndrome_bits.items():
        values[name] = +1.0 if bit == 0 else -1.0

    return SyndromeResult(
        code_name=repeated_result.code_name,
        stabilizer_values=values,
        syndrome_bits=dict(repeated_result.majority_syndrome_bits),
        metadata={
            "source": "repeated_syndrome_majority_vote",
            "rounds": repeated_result.n_rounds,
            "measurement_error_probability": repeated_result.measurement_error_probability,
        },
    )
