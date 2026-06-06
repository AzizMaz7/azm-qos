from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from azmqos import RuntimeManager, RuntimeConfig
from azmqos.states import zero_state
from azmqos_endvqs import default_endvqs_registry, build_all_endvqs_workloads, assemble_m_matrix, assemble_v_vector
from azmqos_logical import repetition_code_3_logical_operator_map, encode_registry_with_code_map
from azmqos_qec import repetition_code_3, circuit_noise_sweep
from azmqos_qec.circuit_benchmarks import run_circuit_level_decoder_sweep

@dataclass
class CircuitLevelQECPipelineResult:
    M: Any
    V: Any
    endvqs_results: list
    circuit_decoder_sweep_result: Any
    metadata: dict

    def summary(self):
        return (
            "CircuitLevelQECPipelineResult\n"
            f"  M shape: {self.M.shape}\n"
            f"  V shape: {self.V.shape}\n"
            f"  END/VQS jobs: {len(self.endvqs_results)}\n"
            f"  decoder sweep points: {len(self.circuit_decoder_sweep_result.points)}"
        )

def run_endvqs_circuit_level_qec_pipeline(
    shots: int = 512,
    repeats: int = 2,
    n_rounds: int = 5,
    n_trials: int = 20,
    seed: int | None = 123,
):
    """Run encoded END/VQS proxy workloads plus circuit-level QEC decoder sweep."""
    physical_registry = default_endvqs_registry()
    code_map = repetition_code_3_logical_operator_map()
    logical_registry = encode_registry_with_code_map(physical_registry, code_map)

    workloads = build_all_endvqs_workloads(registry=logical_registry)
    for workload in workloads:
        n = workload.n_qubits
        workload.state_preparation = lambda params, n=n: zero_state(n)
        workload.parameters = {"n_physical_qubits": n, "logical_code_map": code_map.name}

    manager = RuntimeManager()
    results = [
        manager.run(w, "shot_simulator", RuntimeConfig(shots=shots, repeats=repeats, seed=seed))
        for w in workloads
    ]

    M = assemble_m_matrix(results, dimension=2)
    V = assemble_v_vector(results, dimension=2)

    sweep = run_circuit_level_decoder_sweep(
        code_spec=repetition_code_3(),
        noise_specs=circuit_noise_sweep(two_qubit_errors=[0.0, 0.005, 0.01], readout_error=0.02),
        n_trials=n_trials,
        n_rounds=n_rounds,
        shots=shots,
        seed=seed,
    )

    return CircuitLevelQECPipelineResult(
        M=M,
        V=V,
        endvqs_results=results,
        circuit_decoder_sweep_result=sweep,
        metadata={
            "shots": shots,
            "repeats": repeats,
            "n_rounds": n_rounds,
            "n_trials": n_trials,
            "logical_code_map": code_map.name,
        },
    )
