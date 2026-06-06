from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import time, uuid

@dataclass
class JobResult:
    workload_name: str
    domain: str
    backend_name: str
    backend_type: str
    shots: int
    repeats: int
    exact_total: complex | None
    estimate_mean: complex
    estimate_std: float
    mean_absolute_error: float | None
    term_estimates: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "completed"
    created_at_unix: float = field(default_factory=time.time)

    def summary(self):
        exact = "N/A" if self.exact_total is None else f"{self.exact_total.real:+.8f}"
        mae = "N/A" if self.mean_absolute_error is None else f"{self.mean_absolute_error:.6e}"
        return (
            f"JobResult(job_id={self.job_id[:8]}, workload={self.workload_name}, "
            f"backend={self.backend_name}, shots={self.shots}, repeats={self.repeats}, "
            f"exact={exact}, estimate={self.estimate_mean.real:+.8f}, MAE={mae})"
        )

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "status": self.status,
            "created_at_unix": self.created_at_unix,
            "workload_name": self.workload_name,
            "domain": self.domain,
            "backend_name": self.backend_name,
            "backend_type": self.backend_type,
            "shots": self.shots,
            "repeats": self.repeats,
            "exact_total": None if self.exact_total is None else [self.exact_total.real, self.exact_total.imag],
            "estimate_mean": [self.estimate_mean.real, self.estimate_mean.imag],
            "estimate_std": self.estimate_std,
            "mean_absolute_error": self.mean_absolute_error,
            "term_estimates": self.term_estimates,
            "metadata": self.metadata,
        }
