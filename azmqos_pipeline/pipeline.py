from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np

from azmqos import RuntimeManager, RuntimeConfig, ErrorManager, BackendSelector, BackendSelectionRequest
from azmqos_endvqs import (
    ENDVQSParameterPoint,
    default_endvqs_registry,
    build_all_endvqs_workloads,
    assemble_m_matrix,
    assemble_v_vector,
)
from azmqos_qec import (
    repetition_code_3,
    bell_stabilizer_code,
    ghz_stabilizer_code,
    build_all_qec_workloads,
    infer_syndrome_from_stabilizers,
    MajorityVoteRepetitionDecoder,
    default_logical_observables,
    estimate_qec_resources,
)
from .config import ResearchPipelineConfig
from .mapping import create_placeholder_logical_mapping

@dataclass
class IntegratedPipelineResult:
    config: ResearchPipelineConfig
    backend_name: str
    endvqs_results: list
    qec_results: list
    M: np.ndarray
    V: np.ndarray
    syndrome_result: Any
    decoder_result: Any
    qec_resource_estimate: Any
    logical_mapping_plan: Any
    error_summaries: dict[str, Any]

    def summary(self):
        lines = [
            "AZM-QOS v1.0 IntegratedPipelineResult",
            f"  backend: {self.backend_name}",
            f"  END/VQS results: {len(self.endvqs_results)}",
            f"  QEC results: {len(self.qec_results)}",
            f"  M shape: {self.M.shape}",
            f"  V shape: {self.V.shape}",
            f"  decoder: {self.decoder_result.correction}",
        ]
        return "\n".join(lines)

class IntegratedResearchPipeline:
    def __init__(self, config: ResearchPipelineConfig | None = None):
        self.config = config or ResearchPipelineConfig()
        self.manager = RuntimeManager()
        self.error_manager = ErrorManager()
        self.selector = BackendSelector()

    def _select_qec_code(self):
        if self.config.qec_code == "bell":
            return bell_stabilizer_code()
        if self.config.qec_code == "ghz":
            return ghz_stabilizer_code()
        return repetition_code_3()

    def _select_backend(self, workload):
        if self.config.backend_policy in {"local_statevector", "shot_simulator", "qiskit_aer", "ibm_runtime"}:
            return self.config.backend_policy

        selection = self.selector.select(
            self.manager,
            workload,
            BackendSelectionRequest(require_shots=True, allow_cloud=False),
        )
        return selection.backend_name

    def run(self):
        cfg = self.config

        # 1. Build END/VQS workloads.
        end_registry = default_endvqs_registry()
        parameter_point = ENDVQSParameterPoint(
            theta0=cfg.endvqs_theta0,
            theta1=cfg.endvqs_theta1,
            label=cfg.output_label,
        )
        endvqs_workloads = build_all_endvqs_workloads(
            registry=end_registry,
            parameter_point=parameter_point,
        )

        # 2. Build QEC workloads.
        qec_code = self._select_qec_code()
        qec_workload_set = build_all_qec_workloads(qec_code)
        qec_workloads = qec_workload_set.all_workloads

        # 3. Create logical mapping scaffold.
        mapping_plan = create_placeholder_logical_mapping(endvqs_workloads, qec_code.name)

        # 4. Run END/VQS workloads.
        endvqs_results = []
        for workload in endvqs_workloads:
            backend = self._select_backend(workload)
            result = self.manager.run(
                workload,
                backend,
                RuntimeConfig(shots=cfg.shots, repeats=cfg.repeats, seed=cfg.seed),
            )
            endvqs_results.append(result)

        # 5. Run QEC workloads.
        qec_results = []
        for workload in qec_workloads:
            # QEC demo states have exact state prep, so exact backend is clean.
            backend = "local_statevector" if cfg.backend_policy != "ibm_runtime" else "shot_simulator"
            result = self.manager.run(
                workload,
                backend,
                RuntimeConfig(shots=cfg.shots, repeats=max(1, cfg.repeats), seed=cfg.seed),
            )
            qec_results.append(result)

        # 6. Assemble END/VQS M and V.
        M = assemble_m_matrix(endvqs_results, dimension=end_registry.dimension)
        V = assemble_v_vector(endvqs_results, dimension=end_registry.dimension)

        # 7. Infer QEC syndrome and decode.
        stabilizer_results = [r for r in qec_results if r.workload_name.startswith("qec_stabilizer_")]
        syndrome = infer_syndrome_from_stabilizers(stabilizer_results)
        decoder = MajorityVoteRepetitionDecoder().decode(syndrome)

        # 8. Estimate QEC resources.
        logicals = default_logical_observables(qec_code.name)
        resources = estimate_qec_resources(qec_code, logicals, shots_per_circuit=cfg.shots, rounds=cfg.repeats)

        # 9. Error summaries.
        error_summaries = {}
        for workload in endvqs_workloads:
            allocation = self.error_manager.allocate_shots(workload, total_shots=cfg.shots)
            error_summaries[workload.name] = {
                "allocation_strategy": allocation.strategy,
                "per_term": allocation.per_term,
            }

        return IntegratedPipelineResult(
            config=cfg,
            backend_name=cfg.backend_policy,
            endvqs_results=endvqs_results,
            qec_results=qec_results,
            M=M,
            V=V,
            syndrome_result=syndrome,
            decoder_result=decoder,
            qec_resource_estimate=resources,
            logical_mapping_plan=mapping_plan,
            error_summaries=error_summaries,
        )

def run_integrated_research_pipeline(config: ResearchPipelineConfig | None = None):
    return IntegratedResearchPipeline(config).run()
