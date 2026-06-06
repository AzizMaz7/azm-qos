from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ResearchPipelineConfig:
    """Configuration for the integrated AZM-QOS research pipeline."""

    backend_policy: str = "shot_simulator"
    shots: int = 4096
    repeats: int = 25
    seed: int | None = 123
    endvqs_theta0: float = 0.4
    endvqs_theta1: float = 0.7
    qec_code: str = "repetition3"
    error_confidence: float = 0.95
    output_label: str = "azmqos_v1_integrated_pipeline"

    def summary(self):
        return (
            f"ResearchPipelineConfig(backend_policy={self.backend_policy}, shots={self.shots}, "
            f"repeats={self.repeats}, seed={self.seed}, qec_code={self.qec_code}, "
            f"theta0={self.endvqs_theta0}, theta1={self.endvqs_theta1})"
        )
