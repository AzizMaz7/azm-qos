from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math

from .circuit_noise import CircuitNoiseModelSpec
from .syndrome_circuits import syndrome_spec_to_qiskit

def qiskit_aer_noise_available() -> bool:
    try:
        import qiskit_aer.noise  # noqa: F401
        return True
    except Exception:
        return False

def require_qiskit_aer_noise():
    try:
        from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError
        return NoiseModel, depolarizing_error, ReadoutError
    except Exception as exc:
        raise ImportError(
            "qiskit-aer is required for circuit-level noise models. Install with: "
            "python -m pip install qiskit-aer"
        ) from exc

def build_qiskit_aer_noise_model(spec: CircuitNoiseModelSpec):
    """Build a Qiskit Aer NoiseModel from CircuitNoiseModelSpec."""
    spec.validate()
    NoiseModel, depolarizing_error, ReadoutError = require_qiskit_aer_noise()

    noise_model = NoiseModel()

    p1 = spec.depolarizing.one_qubit_error
    p2 = spec.depolarizing.two_qubit_error
    if p1 > 0:
        error1 = depolarizing_error(p1, 1)
        for gate in ["x", "sx", "h"]:
            noise_model.add_all_qubit_quantum_error(error1, [gate])
    if p2 > 0:
        error2 = depolarizing_error(p2, 2)
        noise_model.add_all_qubit_quantum_error(error2, ["cx"])

    ro = spec.readout.confusion_matrix()
    if spec.readout.p_1_given_0 > 0 or spec.readout.p_0_given_1 > 0:
        readout_error = ReadoutError(ro)
        noise_model.add_all_qubit_readout_error(readout_error)

    return noise_model

@dataclass
class NoisySyndromeCircuitResult:
    stabilizer_name: str
    counts: dict[str, int]
    syndrome_probability_1: float
    shots: int
    noise_spec_label: str
    metadata: dict[str, Any]

    def summary(self):
        return (
            f"NoisySyndromeCircuitResult(stabilizer={self.stabilizer_name}, "
            f"p(syndrome=1)={self.syndrome_probability_1:.6f}, shots={self.shots}, "
            f"noise={self.noise_spec_label})"
        )

def run_noisy_syndrome_circuit_qiskit(spec, noise_spec: CircuitNoiseModelSpec, shots: int = 1024, seed: int | None = 123):
    """Run one syndrome-extraction circuit using Qiskit Aer noise if available."""
    try:
        from qiskit_aer import AerSimulator
    except Exception as exc:
        raise ImportError("qiskit-aer is required. Install with: python -m pip install qiskit-aer") from exc

    qc = syndrome_spec_to_qiskit(spec)
    noise_model = build_qiskit_aer_noise_model(noise_spec)
    sim = AerSimulator(noise_model=noise_model, seed_simulator=seed)
    job = sim.run(qc, shots=shots)
    result = job.result()
    counts = result.get_counts()

    one_counts = 0
    for bitstring, count in counts.items():
        bit = bitstring.replace(" ", "")[-1]
        if bit == "1":
            one_counts += count

    return NoisySyndromeCircuitResult(
        stabilizer_name=spec.stabilizer.name,
        counts=dict(counts),
        syndrome_probability_1=one_counts / shots,
        shots=shots,
        noise_spec_label=noise_spec.label,
        metadata={"qiskit_aer": True},
    )

def estimate_noisy_syndrome_probability_scaffold(noise_spec: CircuitNoiseModelSpec, stabilizer_weight: int):
    """Fallback analytic scaffold if Qiskit Aer is not installed.

    This is not a circuit simulation. It gives a simple monotonic estimate based on
    readout noise and two-qubit error contribution.
    """
    p_ro = 0.5 * (noise_spec.readout.p_1_given_0 + noise_spec.readout.p_0_given_1)
    p_cx = noise_spec.depolarizing.two_qubit_error
    # Approximate probability that at least one parity-affecting error occurs.
    p_gate = 1.0 - (1.0 - p_cx) ** max(stabilizer_weight, 0)
    p = 1.0 - (1.0 - p_ro) * (1.0 - p_gate)
    return max(0.0, min(1.0, p))
