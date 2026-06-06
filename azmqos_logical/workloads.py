from __future__ import annotations
import numpy as np
from azmqos.states import zero_state
from azmqos_endvqs import ENDVQSParameterPoint, build_all_endvqs_workloads
from .encodings import LogicalEncodingMap, repetition_code_block_encoding
from .mapper import encode_term_registry

def logical_zero_state_preparation(params):
    n_qubits = int(params["n_physical_qubits"])
    return zero_state(n_qubits)

def build_logical_endvqs_workloads(
    registry,
    encoding: LogicalEncodingMap | None = None,
    parameter_point: ENDVQSParameterPoint | None = None,
):
    """Build encoded END/VQS workloads from a physical END/VQS registry.

    The default state preparation is a simple encoded zero state scaffold.
    It validates workload construction and execution, but does not yet represent
    a full fault-tolerant encoded END/VQS ansatz.
    """
    encoding = encoding or repetition_code_block_encoding()
    encoded_registry = encode_term_registry(registry, encoding)
    parameter_point = parameter_point or ENDVQSParameterPoint(label="logical_mapping_point")

    workloads = build_all_endvqs_workloads(registry=encoded_registry, parameter_point=parameter_point)

    # Override state-preparation settings for encoded physical qubit count.
    for workload in workloads:
        n = workload.n_qubits
        workload.state_preparation = logical_zero_state_preparation
        workload.parameters = {
            **workload.parameters,
            "n_physical_qubits": n,
            "logical_encoding": encoding.name,
            "block_size": encoding.block_size,
        }
        workload.tags = list(set(workload.tags + ["logical", "encoded", "qec"]))
        workload.metadata["logical_encoding"] = encoding.name
        workload.metadata["encoded_from"] = "endvqs_registry"
    return workloads
