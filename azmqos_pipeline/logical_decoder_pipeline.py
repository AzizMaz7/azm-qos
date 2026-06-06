from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from azmqos import RuntimeManager, RuntimeConfig
from azmqos.states import zero_state
from azmqos_endvqs import default_endvqs_registry, build_all_endvqs_workloads, assemble_m_matrix, assemble_v_vector
from azmqos_logical import repetition_code_3_logical_operator_map, encode_registry_with_code_map
from azmqos_qec import repetition_code_3
from azmqos_qec.decoder_execution import run_decoder_aware_qec_execution

@dataclass
class LogicalDecoderPipelineResult:
    M: Any
    V: Any
    decoder_execution_result: Any
    endvqs_results: list
    metadata: dict

    def summary(self):
        return (
            "LogicalDecoderPipelineResult\n"
            f"  M shape: {self.M.shape}\n"
            f"  V shape: {self.V.shape}\n"
            f"  decoder correction: {self.decoder_execution_result.decoder_result.correction}\n"
            f"  END/VQS jobs: {len(self.endvqs_results)}"
        )

def run_endvqs_logical_decoder_pipeline(
    shots: int = 1024,
    repeats: int = 3,
    syndrome_rounds: int = 5,
    measurement_error_probability: float = 0.0,
    seed: int | None = 123,
):
    """Run encoded END/VQS proxy workloads plus repeated QEC syndrome decoding."""
    physical_registry = default_endvqs_registry()
    code_map = repetition_code_3_logical_operator_map()
    logical_registry = encode_registry_with_code_map(physical_registry, code_map)

    workloads = build_all_endvqs_workloads(registry=logical_registry)
    for workload in workloads:
        n = workload.n_qubits
        workload.state_preparation = lambda params, n=n: zero_state(n)
        workload.parameters = {
            "n_physical_qubits": n,
            "logical_code_map": code_map.name,
        }

    manager = RuntimeManager()
    results = [
        manager.run(w, "shot_simulator", RuntimeConfig(shots=shots, repeats=repeats, seed=seed))
        for w in workloads
    ]

    M = assemble_m_matrix(results, dimension=2)
    V = assemble_v_vector(results, dimension=2)

    decoder_result = run_decoder_aware_qec_execution(
        code_spec=repetition_code_3(),
        n_rounds=syndrome_rounds,
        backend_name="local_statevector",
        shots=shots,
        seed=seed,
        measurement_error_probability=measurement_error_probability,
    )

    return LogicalDecoderPipelineResult(
        M=M,
        V=V,
        decoder_execution_result=decoder_result,
        endvqs_results=results,
        metadata={
            "logical_code_map": code_map.name,
            "shots": shots,
            "repeats": repeats,
            "syndrome_rounds": syndrome_rounds,
            "measurement_error_probability": measurement_error_probability,
        },
    )
