from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass
class QECResourceEstimate:
    code_name: str
    physical_qubits: int
    stabilizer_count: int
    logical_observable_count: int
    estimated_measurement_circuits: int
    estimated_total_shots: int
    notes: str

    def summary(self):
        return (
            f"QECResourceEstimate(code={self.code_name}, physical_qubits={self.physical_qubits}, "
            f"stabilizers={self.stabilizer_count}, logicals={self.logical_observable_count}, "
            f"circuits={self.estimated_measurement_circuits}, total_shots={self.estimated_total_shots})"
        )

def estimate_qec_resources(code, logicals=None, shots_per_circuit: int = 4096, rounds: int = 1):
    logical_count = len(logicals.logicals) if logicals is not None else 0
    circuit_count = (len(code.stabilizers) + logical_count) * rounds
    return QECResourceEstimate(
        code_name=code.name,
        physical_qubits=code.n_physical_qubits,
        stabilizer_count=len(code.stabilizers),
        logical_observable_count=logical_count,
        estimated_measurement_circuits=circuit_count,
        estimated_total_shots=circuit_count * shots_per_circuit,
        notes="Simple first-order estimate; does not include syndrome-extraction ancilla overhead or fault-tolerant scheduling.",
    )
