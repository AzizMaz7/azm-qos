from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
import numpy as np
from azmqos import QuantumWorkload
from azmqos.states import product_ry_state
from .terms import ENDVQSTermRegistry, default_endvqs_registry

@dataclass
class ENDVQSParameterPoint:
    """Minimal parameter point for the template END/VQS plugin.

    In a full implementation, this can be expanded to include electronic and
    nuclear parameters, coherent-state variables, Fukutome parameters, etc.
    """

    theta0: float = 0.4
    theta1: float = 0.7
    label: str = "default_parameter_point"

    def to_dict(self):
        return {"theta0": self.theta0, "theta1": self.theta1, "label": self.label}

def default_endvqs_state_preparation(params: dict[str, Any]):
    """Default two-qubit proxy state preparation.

    Replace this with the real ansatz/circuit mapping for your research plugin.
    """
    return product_ry_state([params.get("theta0", 0.4), params.get("theta1", 0.7)])

def _make_state_preparation(custom_state_preparation: Callable | None):
    return custom_state_preparation or default_endvqs_state_preparation

def build_m_matrix_workloads(
    registry: ENDVQSTermRegistry | None = None,
    parameter_point: ENDVQSParameterPoint | None = None,
    state_preparation: Callable | None = None,
    dimension: int | None = None,
):
    """Build one workload per M-matrix entry.

    Each workload estimates one Pauli-decomposed M_ij entry.
    """
    registry = registry or default_endvqs_registry()
    parameter_point = parameter_point or ENDVQSParameterPoint()
    prep = _make_state_preparation(state_preparation)
    dim = dimension or registry.dimension

    workloads = []
    for i in range(dim):
        for j in range(dim):
            terms = registry.get_m_terms(i, j)
            workload = QuantumWorkload(
                n_qubits=terms[0].n_qubits,
                observables=terms,
                state_preparation=prep,
                parameters=parameter_point.to_dict(),
                name=f"endvqs_M_{i}_{j}",
                domain="endvqs",
                description=f"END/VQS M-matrix entry ({i},{j}).",
                tags=["endvqs", "M-matrix", "plugin"],
                metadata={
                    "plugin": "azmqos_endvqs",
                    "quantity": "M",
                    "indices": [i, j],
                    "parameter_point": parameter_point.to_dict(),
                    "registry_metadata": registry.metadata,
                },
            )
            workloads.append(workload)
    return workloads

def build_v_vector_workloads(
    registry: ENDVQSTermRegistry | None = None,
    parameter_point: ENDVQSParameterPoint | None = None,
    state_preparation: Callable | None = None,
    dimension: int | None = None,
):
    """Build one workload per V-vector entry."""
    registry = registry or default_endvqs_registry()
    parameter_point = parameter_point or ENDVQSParameterPoint()
    prep = _make_state_preparation(state_preparation)
    dim = dimension or registry.dimension

    workloads = []
    for i in range(dim):
        terms = registry.get_v_terms(i)
        workload = QuantumWorkload(
            n_qubits=terms[0].n_qubits,
            observables=terms,
            state_preparation=prep,
            parameters=parameter_point.to_dict(),
            name=f"endvqs_V_{i}",
            domain="endvqs",
            description=f"END/VQS V-vector entry {i}.",
            tags=["endvqs", "V-vector", "plugin"],
            metadata={
                "plugin": "azmqos_endvqs",
                "quantity": "V",
                "index": i,
                "parameter_point": parameter_point.to_dict(),
                "registry_metadata": registry.metadata,
            },
        )
        workloads.append(workload)
    return workloads

def build_all_endvqs_workloads(
    registry: ENDVQSTermRegistry | None = None,
    parameter_point: ENDVQSParameterPoint | None = None,
    state_preparation: Callable | None = None,
    dimension: int | None = None,
):
    """Build all M and V workloads."""
    registry = registry or default_endvqs_registry()
    return (
        build_m_matrix_workloads(registry, parameter_point, state_preparation, dimension)
        + build_v_vector_workloads(registry, parameter_point, state_preparation, dimension)
    )
