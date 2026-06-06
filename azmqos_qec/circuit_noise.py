from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import json

@dataclass
class DepolarizingNoiseSpec:
    one_qubit_error: float = 0.0
    two_qubit_error: float = 0.0

    def validate(self):
        for name, value in [
            ("one_qubit_error", self.one_qubit_error),
            ("two_qubit_error", self.two_qubit_error),
        ]:
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0 and 1.")

@dataclass
class ReadoutNoiseSpec:
    p_1_given_0: float = 0.0
    p_0_given_1: float = 0.0

    def validate(self):
        for name, value in [
            ("p_1_given_0", self.p_1_given_0),
            ("p_0_given_1", self.p_0_given_1),
        ]:
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0 and 1.")

    def confusion_matrix(self):
        return [
            [1.0 - self.p_1_given_0, self.p_1_given_0],
            [self.p_0_given_1, 1.0 - self.p_0_given_1],
        ]

@dataclass
class CircuitNoiseModelSpec:
    """Hardware-independent circuit-level noise model specification."""

    label: str = "simple_circuit_noise_model"
    depolarizing: DepolarizingNoiseSpec = field(default_factory=DepolarizingNoiseSpec)
    readout: ReadoutNoiseSpec = field(default_factory=ReadoutNoiseSpec)
    basis_gates: list[str] = field(default_factory=lambda: ["x", "sx", "rz", "h", "cx", "measure"])
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self):
        self.depolarizing.validate()
        self.readout.validate()

    def summary(self):
        return (
            f"CircuitNoiseModelSpec(label={self.label}, "
            f"p1q={self.depolarizing.one_qubit_error}, "
            f"p2q={self.depolarizing.two_qubit_error}, "
            f"readout_1_given_0={self.readout.p_1_given_0}, "
            f"readout_0_given_1={self.readout.p_0_given_1})"
        )

    def to_dict(self):
        return {
            "label": self.label,
            "depolarizing": {
                "one_qubit_error": self.depolarizing.one_qubit_error,
                "two_qubit_error": self.depolarizing.two_qubit_error,
            },
            "readout": {
                "p_1_given_0": self.readout.p_1_given_0,
                "p_0_given_1": self.readout.p_0_given_1,
                "confusion_matrix": self.readout.confusion_matrix(),
            },
            "basis_gates": self.basis_gates,
            "metadata": self.metadata,
        }

def default_circuit_noise_spec() -> CircuitNoiseModelSpec:
    return CircuitNoiseModelSpec(
        label="default_light_circuit_noise",
        depolarizing=DepolarizingNoiseSpec(one_qubit_error=0.001, two_qubit_error=0.01),
        readout=ReadoutNoiseSpec(p_1_given_0=0.02, p_0_given_1=0.03),
        metadata={"type": "demo_scaffold"},
    )

def circuit_noise_sweep(two_qubit_errors=None, readout_error: float = 0.02):
    if two_qubit_errors is None:
        two_qubit_errors = [0.0, 0.002, 0.005, 0.01, 0.02]
    specs = []
    for p2 in two_qubit_errors:
        specs.append(
            CircuitNoiseModelSpec(
                label=f"circuit_noise_p2_{p2:.4f}",
                depolarizing=DepolarizingNoiseSpec(one_qubit_error=p2 / 10.0, two_qubit_error=float(p2)),
                readout=ReadoutNoiseSpec(p_1_given_0=readout_error, p_0_given_1=readout_error),
                metadata={"sweep_parameter": "two_qubit_error"},
            )
        )
    return specs

def save_circuit_noise_spec_json(spec: CircuitNoiseModelSpec, path):
    path = Path(path)
    path.write_text(json.dumps(spec.to_dict(), indent=2), encoding="utf-8")
    return path
