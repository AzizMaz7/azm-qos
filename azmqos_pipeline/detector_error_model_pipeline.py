from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .detector_graph_pipeline import run_endvqs_detector_graph_pipeline
from azmqos_qec.detector_error_model import detector_graph_to_error_model
from azmqos_qec.matching_benchmarks import run_matching_decoder_benchmark

@dataclass
class DetectorErrorModelPipelineResult:
    detector_graph_pipeline_result: Any
    detector_error_model: Any
    matching_benchmark_result: Any
    metadata: dict

    def summary(self):
        return (
            "DetectorErrorModelPipelineResult\n"
            f"  M shape: {self.detector_graph_pipeline_result.circuit_pipeline_result.M.shape}\n"
            f"  V shape: {self.detector_graph_pipeline_result.circuit_pipeline_result.V.shape}\n"
            f"  detector model instructions: {len(self.detector_error_model.instructions)}\n"
            f"  matching benchmark points: {len(self.matching_benchmark_result.points)}"
        )

def run_endvqs_detector_error_model_pipeline(
    shots: int = 64,
    repeats: int = 1,
    n_rounds: int = 5,
    n_trials: int = 20,
    measurement_error_probability: float = 0.05,
    seed: int | None = 123,
):
    graph_pipeline = run_endvqs_detector_graph_pipeline(
        shots=shots,
        repeats=repeats,
        n_rounds=n_rounds,
        n_trials=3,
        measurement_error_probability=measurement_error_probability,
        seed=seed,
    )

    model = detector_graph_to_error_model(
        graph_pipeline.detector_graph,
        default_probability=measurement_error_probability,
        logical_labels={"0": "logical_failure_placeholder"},
    )

    benchmark = run_matching_decoder_benchmark(
        stabilizer_names=["S_ZZI", "S_IZZ"],
        n_rounds=n_rounds,
        probabilities=[0.0, measurement_error_probability, min(0.25, 2 * measurement_error_probability)],
        n_trials=n_trials,
        seed=seed,
    )

    return DetectorErrorModelPipelineResult(
        detector_graph_pipeline_result=graph_pipeline,
        detector_error_model=model,
        matching_benchmark_result=benchmark,
        metadata={
            "shots": shots,
            "repeats": repeats,
            "n_rounds": n_rounds,
            "n_trials": n_trials,
            "measurement_error_probability": measurement_error_probability,
        },
    )
