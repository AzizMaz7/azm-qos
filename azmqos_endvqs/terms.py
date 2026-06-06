from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from azmqos import PauliTerm

@dataclass
class ENDVQSTermRegistry:
    """Registry for END/VQS-style Pauli terms.

    The registry maps names like M_00, M_01, V_0 into lists of PauliTerm objects.

    The default registry contains proxy terms for software validation. Replace
    them with research-derived Pauli decompositions for production use.
    """

    m_terms: dict[tuple[int, int], list[PauliTerm]] = field(default_factory=dict)
    v_terms: dict[int, list[PauliTerm]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_m_terms(self, i: int, j: int) -> list[PauliTerm]:
        key = (i, j)
        if key in self.m_terms:
            return self.m_terms[key]
        reverse = (j, i)
        if reverse in self.m_terms:
            return self.m_terms[reverse]
        raise KeyError(f"No M-matrix terms registered for index {(i, j)}.")

    def get_v_terms(self, i: int) -> list[PauliTerm]:
        if i not in self.v_terms:
            raise KeyError(f"No V-vector terms registered for index {i}.")
        return self.v_terms[i]

    @property
    def dimension(self) -> int:
        max_idx = -1
        for i, j in self.m_terms:
            max_idx = max(max_idx, i, j)
        for i in self.v_terms:
            max_idx = max(max_idx, i)
        return max_idx + 1

    def summary(self) -> str:
        lines = [
            "ENDVQSTermRegistry",
            f"  dimension: {self.dimension}",
            f"  M entries: {len(self.m_terms)}",
            f"  V entries: {len(self.v_terms)}",
            f"  metadata: {self.metadata}",
        ]
        return "\n".join(lines)

def default_endvqs_registry() -> ENDVQSTermRegistry:
    """Return a small 2x2 proxy registry.

    These proxy terms are not the final physics. They are placeholders that make
    the END/VQS plugin executable and testable.
    """
    m_terms = {
        (0, 0): [
            PauliTerm(1.0, "ZI", label="M00_ZI"),
            PauliTerm(0.125, "ZZ", label="M00_ZZ_correction"),
        ],
        (0, 1): [
            PauliTerm(-0.5, "XX", label="M01_XX"),
            PauliTerm(0.25, "YY", label="M01_YY"),
        ],
        (1, 0): [
            PauliTerm(-0.5, "XX", label="M10_XX"),
            PauliTerm(0.25, "YY", label="M10_YY"),
        ],
        (1, 1): [
            PauliTerm(1.0, "IZ", label="M11_IZ"),
            PauliTerm(0.125, "ZZ", label="M11_ZZ_correction"),
        ],
    }

    v_terms = {
        0: [
            PauliTerm(0.75, "XX", label="V0_XX"),
            PauliTerm(-0.25, "ZI", label="V0_ZI"),
        ],
        1: [
            PauliTerm(-0.25, "YY", label="V1_YY"),
            PauliTerm(0.125, "IZ", label="V1_IZ"),
        ],
    }

    return ENDVQSTermRegistry(
        m_terms=m_terms,
        v_terms=v_terms,
        metadata={
            "type": "proxy",
            "warning": "Replace with real END/VQS Pauli decompositions for research use.",
            "intended_components": ["Mbb", "Mab", "Maa", "Va", "Vb"],
        },
    )

def create_custom_registry(m_terms: dict[tuple[int, int], list[PauliTerm]], v_terms: dict[int, list[PauliTerm]], **metadata):
    """Create a custom registry from user-derived Pauli decompositions."""
    return ENDVQSTermRegistry(m_terms=m_terms, v_terms=v_terms, metadata=metadata)
