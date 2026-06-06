from __future__ import annotations
from dataclasses import dataclass

@dataclass
class LogicalMappingResourceEstimate:
    encoding_name: str
    logical_qubits: int
    physical_qubits: int
    block_size: int
    pauli_term_count: int
    estimated_measurement_circuits: int
    estimated_total_shots: int
    notes: str

    def summary(self):
        return (
            f"LogicalMappingResourceEstimate(encoding={self.encoding_name}, "
            f"logical_qubits={self.logical_qubits}, physical_qubits={self.physical_qubits}, "
            f"terms={self.pauli_term_count}, circuits={self.estimated_measurement_circuits}, "
            f"shots={self.estimated_total_shots})"
        )

def estimate_logical_mapping_resources(registry, encoding, shots_per_term: int = 4096, rounds: int = 1):
    term_count = sum(len(v) for v in registry.m_terms.values()) + sum(len(v) for v in registry.v_terms.values())
    logical_qubits = 0
    for terms in list(registry.m_terms.values()) + list(registry.v_terms.values()):
        for term in terms:
            logical_qubits = max(logical_qubits, len(term.pauli))

    physical_qubits = logical_qubits * encoding.block_size
    circuits = term_count * rounds

    return LogicalMappingResourceEstimate(
        encoding_name=encoding.name,
        logical_qubits=logical_qubits,
        physical_qubits=physical_qubits,
        block_size=encoding.block_size,
        pauli_term_count=term_count,
        estimated_measurement_circuits=circuits,
        estimated_total_shots=circuits * shots_per_term,
        notes="First-order logical-mapping resource estimate; does not include syndrome-extraction ancilla scheduling.",
    )
