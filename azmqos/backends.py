from __future__ import annotations
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any
import numpy as np
from .config import RuntimeConfig
from .job import JobResult
from .pauli import expectation_value

@dataclass
class BackendInfo:
    name: str
    backend_type: str
    description: str
    supports_shots: bool
    supports_exact: bool
    metadata: dict[str, Any] = field(default_factory=dict)

class BackendAdapter(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def info(self) -> BackendInfo:
        raise NotImplementedError

    @abstractmethod
    def run(self, workload, config: RuntimeConfig) -> JobResult:
        raise NotImplementedError

class LocalStatevectorBackend(BackendAdapter):
    def __init__(self, name="local_statevector"):
        super().__init__(name)

    def info(self):
        return BackendInfo(self.name, "statevector", "Exact local dense-statevector backend.", False, True)

    def run(self, workload, config: RuntimeConfig):
        exact_terms = workload.exact_term_values()
        total = sum(exact_terms.values())
        return JobResult(
            workload_name=workload.name,
            domain=workload.domain,
            backend_name=self.name,
            backend_type="statevector",
            shots=0,
            repeats=1,
            exact_total=total,
            estimate_mean=total,
            estimate_std=0.0,
            mean_absolute_error=0.0,
            term_estimates={k: float(np.real_if_close(v)) for k, v in exact_terms.items()},
            metadata={"backend_info": self.info().__dict__},
        )

class ShotSimulatorBackend(BackendAdapter):
    def __init__(self, name="shot_simulator", seed=None):
        super().__init__(name)
        self.rng = np.random.default_rng(seed)

    def info(self):
        return BackendInfo(self.name, "shot_simulator", "Finite-shot Pauli measurement simulator.", True, False)

    def _estimate_raw_pauli(self, raw_expectation, shots):
        mu = float(np.clip(raw_expectation, -1.0, 1.0))
        p_plus = (1.0 + mu) / 2.0
        samples = self.rng.choice([1.0, -1.0], size=shots, p=[p_plus, 1.0 - p_plus])
        return float(np.mean(samples))

    def _run_once(self, workload, shots):
        state = workload.prepare_state()
        total = 0.0 + 0.0j
        term_estimates = {}
        for term in workload.observables:
            raw_mu = float(np.real_if_close(expectation_value(state, term.pauli)))
            raw_est = self._estimate_raw_pauli(raw_mu, shots)
            term_est = term.coeff * raw_est
            total += term_est
            term_estimates[term.name] = float(np.real_if_close(term_est))
        return total, term_estimates

    def run(self, workload, config: RuntimeConfig):
        config.validate()
        totals = []
        last_terms = {}
        exact = workload.exact_total()
        for _ in range(config.repeats):
            total, last_terms = self._run_once(workload, config.shots)
            totals.append(total)
        totals = np.asarray(totals, dtype=complex)
        errors = np.abs(totals - exact)
        return JobResult(
            workload_name=workload.name,
            domain=workload.domain,
            backend_name=self.name,
            backend_type="shot_simulator",
            shots=config.shots,
            repeats=config.repeats,
            exact_total=exact,
            estimate_mean=np.mean(totals),
            estimate_std=float(np.std(np.real(totals), ddof=1)) if config.repeats > 1 else 0.0,
            mean_absolute_error=float(np.mean(errors)),
            term_estimates=last_terms,
            metadata={"backend_info": self.info().__dict__},
        )
