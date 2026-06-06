from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from azmqos import PauliTerm
from azmqos_endvqs import ENDVQSTermRegistry, create_custom_registry

@dataclass
class CodeSpecificLogicalOperatorMap:
    """Code-specific logical Pauli map.

    This maps a single logical-qubit Pauli character into a physical operator
    string for one encoded block.

    Example for a 3-qubit repetition-code scaffold:
        I -> III
        X -> XXX
        Z -> ZII
        Y -> YXX  (proxy, phase ignored at Pauli-string level)
    """

    name: str
    block_size: int
    logical_pauli_map: dict[str, str]
    stabilizers: list[PauliTerm] = field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def encode_char(self, char: str) -> str:
        char = char.upper()
        if char not in self.logical_pauli_map:
            raise ValueError(f"Cannot encode logical Pauli character {char!r}.")
        return self.logical_pauli_map[char]

    def encode_string(self, pauli: str) -> str:
        return "".join(self.encode_char(c) for c in pauli.upper().replace(" ", ""))

    def summary(self):
        lines = [
            f"CodeSpecificLogicalOperatorMap: {self.name}",
            f"  block_size: {self.block_size}",
            f"  description: {self.description}",
            "  logical Pauli map:",
        ]
        for k, v in self.logical_pauli_map.items():
            lines.append(f"    {k} -> {v}")
        if self.stabilizers:
            lines.append("  stabilizers:")
            for s in self.stabilizers:
                lines.append(f"    {s.name}: {s.pauli}")
        return "\n".join(lines)

def repetition_code_3_logical_operator_map() -> CodeSpecificLogicalOperatorMap:
    """Three-qubit bit-flip repetition-code scaffold.

    Stabilizers:
        ZZI, IZZ

    Common logical choices:
        X_L = XXX
        Z_L = ZII  (equivalent to IZI or IIZ up to stabilizers in the codespace)

    Y_L is represented as YXX as a phase-agnostic Pauli-string proxy.
    """
    return CodeSpecificLogicalOperatorMap(
        name="repetition_code_3_logical_map",
        block_size=3,
        logical_pauli_map={
            "I": "III",
            "X": "XXX",
            "Z": "ZII",
            "Y": "YXX",
        },
        stabilizers=[
            PauliTerm(1.0, "ZZI", label="S_ZZI"),
            PauliTerm(1.0, "IZZ", label="S_IZZ"),
        ],
        description="Code-specific scaffold for the 3-qubit bit-flip repetition code.",
        metadata={
            "code_family": "repetition",
            "distance": 3,
            "logical_qubits": 1,
            "warning": "Phase conventions for Y are simplified in this scaffold.",
        },
    )

def bell_pair_logical_operator_map() -> CodeSpecificLogicalOperatorMap:
    """Bell-pair stabilizer/correlation map scaffold."""
    return CodeSpecificLogicalOperatorMap(
        name="bell_pair_logical_map",
        block_size=2,
        logical_pauli_map={
            "I": "II",
            "X": "XX",
            "Z": "ZZ",
            "Y": "YY",
        },
        stabilizers=[
            PauliTerm(1.0, "ZZ", label="S_ZZ"),
            PauliTerm(1.0, "XX", label="S_XX"),
        ],
        description="Bell-pair correlation map scaffold.",
        metadata={"code_family": "bell_demo", "logical_qubits": 1},
    )

def encode_registry_with_code_map(registry: ENDVQSTermRegistry, code_map: CodeSpecificLogicalOperatorMap) -> ENDVQSTermRegistry:
    """Encode an END/VQS registry using a code-specific logical operator map."""
    m_terms = {}
    for key, terms in registry.m_terms.items():
        encoded_terms = []
        for term in terms:
            encoded_terms.append(
                PauliTerm(
                    term.coeff,
                    code_map.encode_string(term.pauli),
                    label=f"{code_map.name}_{term.name}",
                )
            )
        m_terms[key] = encoded_terms

    v_terms = {}
    for key, terms in registry.v_terms.items():
        encoded_terms = []
        for term in terms:
            encoded_terms.append(
                PauliTerm(
                    term.coeff,
                    code_map.encode_string(term.pauli),
                    label=f"{code_map.name}_{term.name}",
                )
            )
        v_terms[key] = encoded_terms

    return create_custom_registry(
        m_terms=m_terms,
        v_terms=v_terms,
        source="code_specific_logical_encoded_registry",
        code_map=code_map.name,
        block_size=code_map.block_size,
        parent_metadata=registry.metadata,
    )
