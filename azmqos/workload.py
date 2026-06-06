from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Any
import numpy as np
from .pauli import PauliTerm, expectation_value, group_commuting_greedy

StatePreparation = Callable[[dict[str, Any]], np.ndarray]

@dataclass
class QuantumWorkload:
    n_qubits: int
    observables: list[PauliTerm]
    state_preparation: StatePreparation | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    name: str = "quantum_workload"
    domain: str = "general"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    circuit: Any | None = None

    def __post_init__(self):
        if self.n_qubits <= 0:
            raise ValueError("n_qubits must be positive.")
        if not self.observables:
            raise ValueError("At least one observable is required.")
        for term in self.observables:
            if term.n_qubits != self.n_qubits:
                raise ValueError(f"{term.name} has wrong qubit count.")
        if self.state_preparation is None and self.circuit is None:
            raise ValueError("Provide either state_preparation or circuit.")

    def prepare_state(self):
        if self.state_preparation is None:
            raise ValueError("This workload has no state_preparation function. Use a circuit backend.")
        state = np.asarray(self.state_preparation(self.parameters), dtype=complex).reshape(-1)
        if state.size != 2 ** self.n_qubits:
            raise ValueError("Prepared state has wrong dimension.")
        norm = np.vdot(state, state)
        if not np.isclose(norm, 1.0, atol=1e-10):
            state = state / np.sqrt(norm)
        return state

    def exact_term_values(self):
        state = self.prepare_state()
        return {t.name: expectation_value(state, t) for t in self.observables}

    def exact_total(self):
        return sum(self.exact_term_values().values())

    def commuting_groups(self):
        return group_commuting_greedy(self.observables)

    def to_dict(self):
        return {
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "n_qubits": self.n_qubits,
            "parameters": self.parameters,
            "tags": self.tags,
            "metadata": self.metadata,
            "has_circuit": self.circuit is not None,
            "observables": [
                {"label": t.label, "pauli": t.pauli, "coeff": [t.coeff.real, t.coeff.imag]}
                for t in self.observables
            ],
        }
