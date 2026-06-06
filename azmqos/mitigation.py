from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass
class ReadoutMitigationModel:
    """Single-qubit readout mitigation placeholder.

    confusion_matrix convention:
        rows = prepared true state
        cols = measured state
        [[P(0|0), P(1|0)],
         [P(0|1), P(1|1)]]
    """
    confusion_matrix: list[list[float]]
    label: str = "single_qubit_readout_model"

    def inverse_matrix(self):
        mat = np.asarray(self.confusion_matrix, dtype=float)
        if mat.shape != (2, 2):
            raise ValueError("Only 2x2 single-qubit confusion matrices are supported in this placeholder.")
        return np.linalg.inv(mat)

    def mitigate_z_expectation(self, measured_z: float) -> float:
        """Approximate mitigation of a single-qubit Z expectation.

        This is a first placeholder useful for architecture tests.
        """
        measured_probs = np.array([(1 + measured_z) / 2, (1 - measured_z) / 2], dtype=float)
        corrected = self.inverse_matrix() @ measured_probs
        corrected = np.clip(corrected, 0.0, 1.0)
        if corrected.sum() > 0:
            corrected = corrected / corrected.sum()
        return float(corrected[0] - corrected[1])

@dataclass
class ZNEResult:
    noise_factors: list[float]
    values: list[float]
    extrapolated_zero_noise: float
    method: str = "linear"

def linear_zero_noise_extrapolation(noise_factors, values) -> ZNEResult:
    """Linear zero-noise extrapolation placeholder.

    Fits value(noise) = a * noise_factor + b and returns b at noise_factor=0.
    """
    x = np.asarray(noise_factors, dtype=float)
    y = np.asarray(values, dtype=float)
    if x.size != y.size or x.size < 2:
        raise ValueError("Need at least two matching noise factors and values.")
    coeff = np.polyfit(x, y, deg=1)
    b = float(coeff[1])
    return ZNEResult(
        noise_factors=list(map(float, noise_factors)),
        values=list(map(float, values)),
        extrapolated_zero_noise=b,
        method="linear",
    )
