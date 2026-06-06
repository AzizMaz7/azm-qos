from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

@dataclass
class ConfidenceInterval:
    mean: float
    std: float
    lower: float
    upper: float
    confidence: float
    n_samples: int
    method: str = "bootstrap"

    def summary(self):
        return (
            f"{self.mean:+.8f} ± {(self.upper - self.lower) / 2:.6e} "
            f"({100*self.confidence:.1f}% {self.method} CI)"
        )

def bootstrap_confidence_interval(
    samples,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int | None = 123,
) -> ConfidenceInterval:
    """Bootstrap confidence interval for the mean of a sample list.

    This works for repeated total estimates or repeated term estimates.
    """
    samples = np.asarray(samples, dtype=float).reshape(-1)
    if samples.size == 0:
        raise ValueError("bootstrap_confidence_interval requires at least one sample.")
    if samples.size == 1:
        return ConfidenceInterval(
            mean=float(samples[0]),
            std=0.0,
            lower=float(samples[0]),
            upper=float(samples[0]),
            confidence=confidence,
            n_samples=1,
            method="bootstrap_degenerate",
        )

    rng = np.random.default_rng(seed)
    means = []
    for _ in range(int(n_resamples)):
        resample = rng.choice(samples, size=samples.size, replace=True)
        means.append(float(np.mean(resample)))

    alpha = 1.0 - confidence
    lower = float(np.quantile(means, alpha / 2.0))
    upper = float(np.quantile(means, 1.0 - alpha / 2.0))

    return ConfidenceInterval(
        mean=float(np.mean(samples)),
        std=float(np.std(samples, ddof=1)),
        lower=lower,
        upper=upper,
        confidence=confidence,
        n_samples=int(samples.size),
        method="bootstrap",
    )

def binomial_pauli_standard_error(expectation: float, shots: int) -> float:
    """Standard error for a Pauli measurement with outcomes ±1.

    Var(X) = 1 - mu^2, so SE(mean) = sqrt((1 - mu^2)/shots).
    """
    if shots <= 0:
        raise ValueError("shots must be positive.")
    mu = float(np.clip(expectation, -1.0, 1.0))
    return math.sqrt(max(0.0, 1.0 - mu * mu) / shots)
