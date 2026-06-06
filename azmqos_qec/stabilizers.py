from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from azmqos import PauliTerm
from azmqos.states import bell_state, ghz_state, zero_state
import numpy as np

@dataclass
class StabilizerCodeSpec:
    """Minimal stabilizer-code specification for AZM-QOS QEC workloads."""

    name: str
    n_physical_qubits: int
    stabilizers: list[PauliTerm]
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    state_preparation: Any | None = None

    def summary(self):
        lines = [
            f"StabilizerCodeSpec: {self.name}",
            f"  physical qubits: {self.n_physical_qubits}",
            f"  stabilizers: {len(self.stabilizers)}",
            f"  description: {self.description}",
        ]
        for s in self.stabilizers:
            lines.append(f"    {s.name}: {s.pauli}")
        return "\n".join(lines)

def bell_stabilizer_code() -> StabilizerCodeSpec:
    return StabilizerCodeSpec(
        name="bell_pair_stabilizer_demo",
        n_physical_qubits=2,
        stabilizers=[
            PauliTerm(1.0, "ZZ", label="S_ZZ"),
            PauliTerm(1.0, "XX", label="S_XX"),
        ],
        description="Two-qubit Bell-state stabilizer demonstration.",
        metadata={"type": "demo"},
        state_preparation=lambda params: bell_state(),
    )

def ghz_stabilizer_code() -> StabilizerCodeSpec:
    return StabilizerCodeSpec(
        name="ghz_3_stabilizer_demo",
        n_physical_qubits=3,
        stabilizers=[
            PauliTerm(1.0, "ZZI", label="S_ZZI"),
            PauliTerm(1.0, "IZZ", label="S_IZZ"),
            PauliTerm(1.0, "XXX", label="S_XXX"),
        ],
        description="Three-qubit GHZ stabilizer demonstration.",
        metadata={"type": "demo"},
        state_preparation=lambda params: ghz_state(3),
    )

def repetition_code_3() -> StabilizerCodeSpec:
    """Three-qubit repetition-code style demo.

    This is a bit-flip repetition code demonstration with Z-parity stabilizers.
    The default state is |000>, so stabilizer expectations are +1.
    """
    return StabilizerCodeSpec(
        name="repetition_code_3_demo",
        n_physical_qubits=3,
        stabilizers=[
            PauliTerm(1.0, "ZZI", label="S_ZZI"),
            PauliTerm(1.0, "IZZ", label="S_IZZ"),
        ],
        description="Three-qubit bit-flip repetition-code demonstration.",
        metadata={"type": "demo", "distance": 3, "logical_qubits": 1},
        state_preparation=lambda params: zero_state(3),
    )
