from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .decoders import DecoderInterface, MajorityVoteRepetitionDecoder, DecoderResult
from .rounds import (
    RepeatedSyndromeResult,
    run_repeated_syndrome_rounds,
    repeated_syndrome_to_syndrome_result,
)

@dataclass
class CorrectionHistoryEntry:
    round_window: str
    correction: str
    confidence: float
    syndrome_bits: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class DecoderAwareExecutionResult:
    """Result of repeated syndrome execution plus decoder decision."""

    code_name: str
    repeated_syndrome_result: RepeatedSyndromeResult
    decoder_result: DecoderResult
    correction_history: list[CorrectionHistoryEntry]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [
            f"DecoderAwareExecutionResult(code={self.code_name})",
            self.repeated_syndrome_result.summary(),
            self.decoder_result.summary(),
            "Correction history:",
        ]
        for entry in self.correction_history:
            lines.append(
                f"  {entry.round_window}: correction={entry.correction}, confidence={entry.confidence:.3f}"
            )
        return "\n".join(lines)

def run_decoder_aware_qec_execution(
    code_spec,
    n_rounds: int = 3,
    decoder: DecoderInterface | None = None,
    backend_name: str = "local_statevector",
    shots: int = 4096,
    seed: int | None = 123,
    measurement_error_probability: float = 0.0,
) -> DecoderAwareExecutionResult:
    """Run repeated syndrome rounds and decode the majority syndrome."""
    decoder = decoder or MajorityVoteRepetitionDecoder()
    repeated = run_repeated_syndrome_rounds(
        code_spec=code_spec,
        n_rounds=n_rounds,
        backend_name=backend_name,
        shots=shots,
        seed=seed,
        measurement_error_probability=measurement_error_probability,
    )
    majority_syndrome = repeated_syndrome_to_syndrome_result(repeated)
    decoded = decoder.decode(majority_syndrome)

    history = [
        CorrectionHistoryEntry(
            round_window=f"rounds_0_to_{n_rounds-1}",
            correction=decoded.correction,
            confidence=decoded.confidence,
            syndrome_bits=dict(decoded.syndrome_bits),
            metadata={"decoder": decoder.__class__.__name__},
        )
    ]

    return DecoderAwareExecutionResult(
        code_name=code_spec.name,
        repeated_syndrome_result=repeated,
        decoder_result=decoded,
        correction_history=history,
        metadata={
            "backend_name": backend_name,
            "shots": shots,
            "n_rounds": n_rounds,
            "measurement_error_probability": measurement_error_probability,
        },
    )
