from __future__ import annotations
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any

@dataclass
class DecoderResult:
    correction: str
    confidence: float
    syndrome_bits: dict[str, int]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"DecoderResult(correction={self.correction}, "
            f"confidence={self.confidence:.3f}, syndrome={self.syndrome_bits})"
        )

class DecoderInterface(ABC):
    @abstractmethod
    def decode(self, syndrome_result) -> DecoderResult:
        raise NotImplementedError

class MajorityVoteRepetitionDecoder(DecoderInterface):
    """Tiny repetition-code decoder placeholder.

    For the 3-qubit repetition code with stabilizers ZZI and IZZ:
      00 -> no correction
      10 -> flip q0/q1 boundary ambiguity placeholder
      01 -> flip q2/q1 boundary ambiguity placeholder
      11 -> flip middle qubit
    """

    def decode(self, syndrome_result):
        bits = syndrome_result.syndrome_bits
        values = list(bits.values())
        if not values or all(v == 0 for v in values):
            correction = "I"
            confidence = 1.0
        elif len(values) >= 2 and values[0] == 1 and values[1] == 1:
            correction = "X_on_middle_qubit_proxy"
            confidence = 0.8
        elif values[0] == 1:
            correction = "X_on_left_boundary_proxy"
            confidence = 0.6
        else:
            correction = "X_on_right_boundary_proxy"
            confidence = 0.6
        return DecoderResult(correction=correction, confidence=confidence, syndrome_bits=bits, metadata={"decoder": "majority_vote_proxy"})

class LookupTableDecoderPlaceholder(DecoderInterface):
    def __init__(self, table=None):
        self.table = table or {}

    def decode(self, syndrome_result):
        key = tuple(syndrome_result.syndrome_bits.values())
        correction = self.table.get(key, "unknown_correction_placeholder")
        return DecoderResult(
            correction=correction,
            confidence=0.5 if correction.startswith("unknown") else 0.9,
            syndrome_bits=syndrome_result.syndrome_bits,
            metadata={"decoder": "lookup_table_placeholder"},
        )
