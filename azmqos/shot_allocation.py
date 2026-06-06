from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from .pauli import expectation_value

@dataclass
class ShotAllocation:
    total_shots: int
    per_term: dict[str, int]
    strategy: str
    metadata: dict

    def summary(self):
        lines = [
            f"ShotAllocation(strategy={self.strategy}, total_shots={self.total_shots})"
        ]
        for key, value in self.per_term.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

def uniform_shot_allocation(workload, total_shots: int) -> ShotAllocation:
    """Allocate shots equally among observable terms."""
    if total_shots <= 0:
        raise ValueError("total_shots must be positive.")
    n_terms = len(workload.observables)
    base = total_shots // n_terms
    remainder = total_shots % n_terms
    per = {}
    for i, term in enumerate(workload.observables):
        per[term.name] = base + (1 if i < remainder else 0)
    return ShotAllocation(total_shots=total_shots, per_term=per, strategy="uniform", metadata={})

def coefficient_weighted_shot_allocation(workload, total_shots: int, min_shots_per_term: int = 16) -> ShotAllocation:
    """Allocate more shots to Pauli terms with larger absolute coefficients."""
    if total_shots <= 0:
        raise ValueError("total_shots must be positive.")
    n_terms = len(workload.observables)
    if total_shots < n_terms * min_shots_per_term:
        min_shots_per_term = max(1, total_shots // n_terms)

    weights = np.asarray([abs(t.coeff) for t in workload.observables], dtype=float)
    if np.allclose(weights, 0.0):
        return uniform_shot_allocation(workload, total_shots)

    remaining = total_shots - n_terms * min_shots_per_term
    weights = weights / np.sum(weights)
    extra = np.floor(weights * remaining).astype(int)
    shortfall = remaining - int(np.sum(extra))

    # distribute leftover shots to largest fractional need
    fractional = weights * remaining - extra
    order = np.argsort(-fractional)
    for idx in order[:shortfall]:
        extra[idx] += 1

    per = {}
    for term, add in zip(workload.observables, extra):
        per[term.name] = int(min_shots_per_term + add)

    return ShotAllocation(
        total_shots=int(sum(per.values())),
        per_term=per,
        strategy="coefficient_weighted",
        metadata={"min_shots_per_term": min_shots_per_term},
    )

def variance_aware_shot_allocation(workload, total_shots: int, min_shots_per_term: int = 16) -> ShotAllocation:
    """Allocate shots using coefficient magnitude and estimated Pauli variance.

    Weight_i ∝ |c_i| sqrt(1 - <P_i>^2).
    This uses the workload state-preparation function, so it works for simulator-style workloads.
    """
    if workload.state_preparation is None:
        return coefficient_weighted_shot_allocation(workload, total_shots, min_shots_per_term)

    state = workload.prepare_state()
    weights = []
    variances = {}
    for term in workload.observables:
        raw_mu = float(np.real_if_close(expectation_value(state, term.pauli)))
        var = max(0.0, 1.0 - raw_mu * raw_mu)
        variances[term.name] = var
        weights.append(abs(term.coeff) * math.sqrt(var))

    weights = np.asarray(weights, dtype=float)
    if np.allclose(weights, 0.0):
        return uniform_shot_allocation(workload, total_shots)

    n_terms = len(workload.observables)
    if total_shots < n_terms * min_shots_per_term:
        min_shots_per_term = max(1, total_shots // n_terms)

    remaining = total_shots - n_terms * min_shots_per_term
    weights = weights / np.sum(weights)
    extra = np.floor(weights * remaining).astype(int)
    shortfall = remaining - int(np.sum(extra))
    fractional = weights * remaining - extra
    order = np.argsort(-fractional)
    for idx in order[:shortfall]:
        extra[idx] += 1

    per = {}
    for term, add in zip(workload.observables, extra):
        per[term.name] = int(min_shots_per_term + add)

    return ShotAllocation(
        total_shots=int(sum(per.values())),
        per_term=per,
        strategy="variance_aware",
        metadata={"min_shots_per_term": min_shots_per_term, "estimated_variances": variances},
    )
