from __future__ import annotations
from typing import Any
from .pauli import PauliTerm
from .workload import QuantumWorkload

def qiskit_available() -> bool:
    try:
        import qiskit  # noqa: F401
        return True
    except Exception:
        return False

def require_qiskit():
    try:
        import qiskit
        return qiskit
    except Exception as exc:
        raise ImportError(
            "Qiskit is required for this feature. Install it with:\n"
            "python -m pip install qiskit qiskit-aer"
        ) from exc

def require_qiskit_aer():
    try:
        from qiskit_aer import AerSimulator
        return AerSimulator
    except Exception as exc:
        raise ImportError(
            "qiskit-aer is required for this backend. Install it with:\n"
            "python -m pip install qiskit-aer"
        ) from exc

def make_qiskit_circuit_workload(circuit: Any, observables: list[PauliTerm], name="qiskit_circuit_workload", domain="qiskit", description="", metadata=None):
    return QuantumWorkload(
        n_qubits=circuit.num_qubits,
        observables=observables,
        state_preparation=None,
        parameters={},
        name=name,
        domain=domain,
        description=description,
        metadata=metadata or {},
        circuit=circuit,
    )

def pauli_terms_to_sparse_pauli_op(terms: list[PauliTerm]):
    require_qiskit()
    try:
        from qiskit.quantum_info import SparsePauliOp
    except Exception as exc:
        raise ImportError("Your Qiskit version does not expose SparsePauliOp.") from exc
    return SparsePauliOp([t.pauli for t in terms], coeffs=[t.coeff for t in terms])

def export_circuit_openqasm(circuit, path: str | None = None) -> str:
    require_qiskit()
    text = None
    try:
        from qiskit import qasm2
        text = qasm2.dumps(circuit)
    except Exception:
        pass
    if text is None:
        try:
            text = circuit.qasm()
        except Exception as exc:
            raise RuntimeError("Could not export QASM from this Qiskit version.") from exc
    if path is not None:
        from pathlib import Path
        Path(path).write_text(text, encoding="utf-8")
    return text

def add_pauli_measurement_basis(circuit, pauli: str):
    require_qiskit()
    qc = circuit.copy()
    for q, p in enumerate(reversed(pauli)):
        if p == "X":
            qc.h(q)
        elif p == "Y":
            qc.sdg(q)
            qc.h(q)
        elif p in ("Z", "I"):
            pass
        else:
            raise ValueError("Invalid Pauli character.")
    qc.measure_all()
    return qc

def expectation_from_counts(counts: dict[str, int], pauli: str) -> float:
    shots = sum(counts.values())
    if shots == 0:
        raise ValueError("No shots in counts.")
    total = 0.0
    pauli_reversed = pauli[::-1]
    for bitstring, count in counts.items():
        bits = bitstring.replace(" ", "")[::-1]
        eigenvalue = 1
        for i, p in enumerate(pauli_reversed):
            if p == "I":
                continue
            bit = bits[i]
            eigenvalue *= 1 if bit == "0" else -1
        total += eigenvalue * count
    return total / shots
