from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from azmqos import PauliTerm
from azmqos_endvqs import ENDVQSTermRegistry, create_custom_registry
from .encodings import LogicalEncodingMap, repetition_code_block_encoding

@dataclass
class EncodedPauliTerm:
    source_term: PauliTerm
    encoded_term: PauliTerm
    encoding_name: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return f"{self.source_term.name}: {self.source_term.pauli} -> {self.encoded_term.pauli}"

def encode_pauli_string(pauli: str, encoding: LogicalEncodingMap | None = None) -> str:
    encoding = encoding or repetition_code_block_encoding()
    return encoding.encode_string(pauli)

def encode_pauli_term(term: PauliTerm, encoding: LogicalEncodingMap | None = None, label_prefix: str = "logical") -> EncodedPauliTerm:
    encoding = encoding or repetition_code_block_encoding()
    encoded_pauli = encode_pauli_string(term.pauli, encoding)
    label = f"{label_prefix}_{term.name}"
    encoded = PauliTerm(term.coeff, encoded_pauli, label=label)
    return EncodedPauliTerm(
        source_term=term,
        encoded_term=encoded,
        encoding_name=encoding.name,
        metadata={"source_pauli": term.pauli, "encoded_pauli": encoded_pauli},
    )

def encode_term_registry(registry: ENDVQSTermRegistry, encoding: LogicalEncodingMap | None = None) -> ENDVQSTermRegistry:
    """Encode all Pauli terms in an END/VQS registry."""
    encoding = encoding or repetition_code_block_encoding()

    m_terms = {}
    for key, terms in registry.m_terms.items():
        m_terms[key] = [encode_pauli_term(t, encoding).encoded_term for t in terms]

    v_terms = {}
    for key, terms in registry.v_terms.items():
        v_terms[key] = [encode_pauli_term(t, encoding).encoded_term for t in terms]

    return create_custom_registry(
        m_terms=m_terms,
        v_terms=v_terms,
        source="logical_encoded_registry",
        encoding=encoding.name,
        block_size=encoding.block_size,
        parent_metadata=registry.metadata,
    )

def compare_registry_sizes(physical_registry: ENDVQSTermRegistry, logical_registry: ENDVQSTermRegistry):
    """Return basic size comparison between physical and encoded registries."""
    physical_lengths = []
    logical_lengths = []

    for terms in physical_registry.m_terms.values():
        physical_lengths.extend(len(t.pauli) for t in terms)
    for terms in physical_registry.v_terms.values():
        physical_lengths.extend(len(t.pauli) for t in terms)
    for terms in logical_registry.m_terms.values():
        logical_lengths.extend(len(t.pauli) for t in terms)
    for terms in logical_registry.v_terms.values():
        logical_lengths.extend(len(t.pauli) for t in terms)

    return {
        "physical_term_count": len(physical_lengths),
        "logical_term_count": len(logical_lengths),
        "physical_max_pauli_length": max(physical_lengths) if physical_lengths else 0,
        "logical_max_pauli_length": max(logical_lengths) if logical_lengths else 0,
        "physical_avg_pauli_length": sum(physical_lengths) / len(physical_lengths) if physical_lengths else 0,
        "logical_avg_pauli_length": sum(logical_lengths) / len(logical_lengths) if logical_lengths else 0,
    }
