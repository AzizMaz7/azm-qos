from dataclasses import dataclass, field
from typing import Any

@dataclass
class RuntimeConfig:
    shots: int = 4096
    repeats: int = 1
    seed: int | None = None
    precision_target: float | None = None
    max_cost: float | None = None
    optimization_level: int = 1
    backend_options: dict[str, Any] = field(default_factory=dict)

    def validate(self):
        if self.shots <= 0:
            raise ValueError("shots must be positive.")
        if self.repeats <= 0:
            raise ValueError("repeats must be positive.")
