from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np

@dataclass
class QECNoiseModel:
    """Simple QEC noise model scaffold.

    v1.5 primarily uses measurement_error_probability to flip syndrome bits.
    data_error_probability and gate_error_probability are included as placeholders
    for future circuit-level noise.
    """

    measurement_error_probability: float = 0.0
    data_error_probability: float = 0.0
    gate_error_probability: float = 0.0
    label: str = "simple_qec_noise_model"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self):
        for name, value in [
            ("measurement_error_probability", self.measurement_error_probability),
            ("data_error_probability", self.data_error_probability),
            ("gate_error_probability", self.gate_error_probability),
        ]:
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be between 0 and 1.")

    def summary(self):
        return (
            f"QECNoiseModel(label={self.label}, "
            f"measurement_error={self.measurement_error_probability}, "
            f"data_error={self.data_error_probability}, "
            f"gate_error={self.gate_error_probability})"
        )

def measurement_noise_sweep(probabilities=None):
    if probabilities is None:
        probabilities = [0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25]
    return [
        QECNoiseModel(
            measurement_error_probability=float(p),
            label=f"measurement_noise_{p:.4f}",
            metadata={"sweep_parameter": "measurement_error_probability"},
        )
        for p in probabilities
    ]

def sample_bit_flip(bit: int, probability: float, rng=None):
    rng = rng or np.random.default_rng()
    return 1 - bit if rng.random() < probability else bit
