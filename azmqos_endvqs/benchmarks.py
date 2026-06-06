from __future__ import annotations
from azmqos import RuntimeManager, RuntimeConfig, ErrorManager
from .terms import default_endvqs_registry
from .builders import ENDVQSParameterPoint, build_all_endvqs_workloads
from .assemblers import assemble_m_matrix, assemble_v_vector

def run_endvqs_benchmark(
    backend_name: str = "shot_simulator",
    shots: int = 4096,
    repeats: int = 25,
    seed: int | None = 123,
    parameter_point: ENDVQSParameterPoint | None = None,
):
    """Run a complete proxy END/VQS benchmark."""
    registry = default_endvqs_registry()
    parameter_point = parameter_point or ENDVQSParameterPoint()
    workloads = build_all_endvqs_workloads(registry=registry, parameter_point=parameter_point)

    manager = RuntimeManager()
    results = []
    for workload in workloads:
        result = manager.run(
            workload,
            backend_name=backend_name,
            config=RuntimeConfig(shots=shots, repeats=repeats, seed=seed),
        )
        results.append(result)

    M = assemble_m_matrix(results, dimension=registry.dimension)
    V = assemble_v_vector(results, dimension=registry.dimension)

    error_manager = ErrorManager()
    allocations = {
        workload.name: error_manager.allocate_shots(workload, total_shots=shots, strategy="variance_aware")
        for workload in workloads
    }

    return {
        "registry": registry,
        "parameter_point": parameter_point,
        "workloads": workloads,
        "results": results,
        "M": M,
        "V": V,
        "allocations": allocations,
    }
