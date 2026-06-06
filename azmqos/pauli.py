from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import numpy as np

_SINGLE = {
    "I": np.array([[1, 0], [0, 1]], dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}

@dataclass(frozen=True)
class PauliTerm:
    coeff: complex
    pauli: str
    label: str | None = None

    def __post_init__(self):
        p = self.pauli.upper().replace(" ", "")
        if not p or any(c not in _SINGLE for c in p):
            raise ValueError("Pauli string must contain only I, X, Y, Z.")
        object.__setattr__(self, "pauli", p)
        object.__setattr__(self, "coeff", complex(self.coeff))

    @property
    def n_qubits(self):
        return len(self.pauli)

    @property
    def name(self):
        return self.label or self.pauli

@dataclass
class PauliOperator:
    terms: list[PauliTerm]
    name: str = "pauli_operator"

    def __post_init__(self):
        if not self.terms:
            raise ValueError("PauliOperator needs at least one term.")
        n = self.terms[0].n_qubits
        if any(t.n_qubits != n for t in self.terms):
            raise ValueError("All Pauli terms must have the same qubit count.")

    @property
    def n_qubits(self):
        return self.terms[0].n_qubits

    def expectation(self, state):
        return sum(expectation_value(state, t) for t in self.terms)

def pauli_matrix(pauli: str):
    pauli = pauli.upper().replace(" ", "")
    mat = np.array([[1.0 + 0.0j]])
    for c in pauli:
        if c not in _SINGLE:
            raise ValueError("Invalid Pauli character.")
        mat = np.kron(mat, _SINGLE[c])
    return mat

def expectation_value(state, term: PauliTerm | str):
    if isinstance(term, str):
        term = PauliTerm(1.0, term)
    state = np.asarray(state, dtype=complex).reshape(-1)
    if state.size != 2 ** term.n_qubits:
        raise ValueError("State dimension does not match Pauli string.")
    norm = np.vdot(state, state)
    if not np.isclose(norm, 1.0, atol=1e-10):
        state = state / np.sqrt(norm)
    return term.coeff * np.vdot(state, pauli_matrix(term.pauli) @ state)

def commutes(p: str, q: str):
    p = p.upper().replace(" ", "")
    q = q.upper().replace(" ", "")
    if len(p) != len(q):
        raise ValueError("Pauli strings must have the same length.")
    anti = 0
    for a, b in zip(p, q):
        if a == "I" or b == "I" or a == b:
            continue
        anti += 1
    return anti % 2 == 0

def group_commuting_greedy(terms: Iterable[PauliTerm]):
    groups = []
    for t in terms:
        for g in groups:
            if all(commutes(t.pauli, u.pauli) for u in g):
                g.append(t)
                break
        else:
            groups.append([t])
    return groups
