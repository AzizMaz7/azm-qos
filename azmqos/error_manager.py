from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .uncertainty import bootstrap_confidence_interval, ConfidenceInterval
from .shot_allocation import (
    uniform_shot_allocation,
    coefficient_weighted_shot_allocation,
    variance_aware_shot_allocation,
    ShotAllocation,
)

@dataclass
class ErrorAnalysis:
    total_ci: ConfidenceInterval | None
    shot_allocation: ShotAllocation | None
    mitigation_summary: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = ["ErrorAnalysis"]
        if self.total_ci is not None:
            lines.append(f"  Total estimate CI: {self.total_ci.summary()}")
        if self.shot_allocation is not None:
            lines.append(f"  Shot allocation: {self.shot_allocation.strategy}")
        for key, value in self.mitigation_summary.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

class ErrorManager:
    """Architecture entry point for uncertainty and error-management workflows."""

    def bootstrap_total_from_samples(self, samples, confidence=0.95, n_resamples=2000, seed=123):
        return bootstrap_confidence_interval(samples, confidence=confidence, n_resamples=n_resamples, seed=seed)

    def allocate_shots(self, workload, total_shots: int, strategy: str = "variance_aware", min_shots_per_term: int = 16):
        if strategy == "uniform":
            return uniform_shot_allocation(workload, total_shots)
        if strategy == "coefficient_weighted":
            return coefficient_weighted_shot_allocation(workload, total_shots, min_shots_per_term)
        if strategy == "variance_aware":
            return variance_aware_shot_allocation(workload, total_shots, min_shots_per_term)
        raise ValueError(f"Unknown shot allocation strategy: {strategy}")

    def analyze_result(self, result, repeated_total_samples=None, workload=None, total_shots=None, allocation_strategy="variance_aware"):
        ci = None
        allocation = None

        if repeated_total_samples is not None:
            ci = self.bootstrap_total_from_samples(repeated_total_samples)

        if workload is not None and total_shots is not None:
            allocation = self.allocate_shots(workload, total_shots, strategy=allocation_strategy)

        return ErrorAnalysis(
            total_ci=ci,
            shot_allocation=allocation,
            mitigation_summary={
                "readout_mitigation": "placeholder_available",
                "zero_noise_extrapolation": "placeholder_available",
            },
        )
