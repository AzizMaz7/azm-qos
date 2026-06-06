from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from azmqos import PauliTerm

@dataclass
class StabilizerMeasurementStep:
    gate: str
    control: int | None
    target: int
    note: str = ""

@dataclass
class SyndromeExtractionCircuitSpec:
    """Hardware-independent syndrome-extraction circuit specification."""

    stabilizer: PauliTerm
    data_qubits: list[int]
    ancilla_qubit: int
    steps: list[StabilizerMeasurementStep]
    basis_change: list[StabilizerMeasurementStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [
            f"SyndromeExtractionCircuitSpec(stabilizer={self.stabilizer.name}:{self.stabilizer.pauli})",
            f"  data_qubits: {self.data_qubits}",
            f"  ancilla_qubit: {self.ancilla_qubit}",
            "  basis changes:",
        ]
        if self.basis_change:
            for step in self.basis_change:
                lines.append(f"    {step.gate} target={step.target} note={step.note}")
        else:
            lines.append("    none")
        lines.append("  entangling/measurement steps:")
        for step in self.steps:
            lines.append(f"    {step.gate} control={step.control} target={step.target} note={step.note}")
        return "\n".join(lines)

def build_syndrome_extraction_spec(stabilizer: PauliTerm, ancilla_qubit: int | None = None) -> SyndromeExtractionCircuitSpec:
    """Build a syndrome-extraction spec for a Pauli stabilizer.

    This is a scaffold:
    - Z stabilizers use CNOT(data -> ancilla)
    - X stabilizers use H basis changes on data, then CNOT(data -> ancilla)
    - Y stabilizers use Sdg + H basis changes on data, then CNOT(data -> ancilla)

    Production fault-tolerant circuits need scheduling and hook-error analysis.
    """
    n = stabilizer.n_qubits
    anc = n if ancilla_qubit is None else ancilla_qubit
    data = list(range(n))
    basis = []
    steps = []

    # Qubit indexing uses left-to-right Pauli position -> data qubit index.
    for q, p in enumerate(stabilizer.pauli):
        if p == "I":
            continue
        if p == "X":
            basis.append(StabilizerMeasurementStep("H", None, q, "Rotate X measurement into Z basis."))
        elif p == "Y":
            basis.append(StabilizerMeasurementStep("SDG", None, q, "First part of Y-to-Z basis rotation."))
            basis.append(StabilizerMeasurementStep("H", None, q, "Second part of Y-to-Z basis rotation."))
        elif p == "Z":
            pass
        else:
            raise ValueError(f"Invalid Pauli character {p!r}.")
        steps.append(StabilizerMeasurementStep("CX", q, anc, "Entangle data parity into ancilla."))

    steps.append(StabilizerMeasurementStep("MEASURE", None, anc, "Measure ancilla to obtain syndrome bit."))

    return SyndromeExtractionCircuitSpec(
        stabilizer=stabilizer,
        data_qubits=data,
        ancilla_qubit=anc,
        basis_change=basis,
        steps=steps,
        metadata={"type": "syndrome_extraction_scaffold"},
    )

def build_syndrome_extraction_specs_for_code(code_spec) -> list[SyndromeExtractionCircuitSpec]:
    return [build_syndrome_extraction_spec(stab) for stab in code_spec.stabilizers]

def syndrome_spec_to_qiskit(spec: SyndromeExtractionCircuitSpec):
    """Convert a syndrome-extraction spec to a Qiskit QuantumCircuit if Qiskit is installed."""
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:
        raise ImportError("Qiskit is required for syndrome_spec_to_qiskit. Install with: python -m pip install qiskit") from exc

    n_total = max(spec.data_qubits + [spec.ancilla_qubit]) + 1
    qc = QuantumCircuit(n_total, 1)

    for step in spec.basis_change:
        if step.gate == "H":
            qc.h(step.target)
        elif step.gate == "SDG":
            qc.sdg(step.target)

    for step in spec.steps:
        if step.gate == "CX":
            qc.cx(step.control, step.target)
        elif step.gate == "MEASURE":
            qc.measure(step.target, 0)

    return qc
