from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .logical_decoder_pipeline import run_endvqs_logical_decoder_pipeline
from azmqos_qec.decoder_benchmarks import run_decoder_noise_sweep
from azmqos_qec.stabilizers import repetition_code_3

@dataclass
class NoiseAwarePipelineResult:
    encoded_pipeline_result: Any
    decoder_benchmark_result: Any
    metadata: dict

    def summary(self):
        return (
            "NoiseAwarePipelineResult\n"
            f"  encoded pipeline correction: {self.encoded_pipeline_result.decoder_execution_result.decoder_result.correction}\n"
            f"  benchmark points: {len(self.decoder_benchmark_result.points)}\n"
            f"  M shape: {self.encoded_pipeline_result.M.shape}\n"
            f"  V shape: {self.encoded_pipeline_result.V.shape}"
        )

def run_noise_aware_endvqs_qec_pipeline(
    shots: int = 512,
    repeats: int = 3,
    syndrome_rounds: int = 5,
    benchmark_trials: int = 50,
    probabilities=None,
    seed: int | None = 123,
):
    """Run encoded END/VQS pipeline and decoder noise sweep."""
    encoded = run_endvqs_logical_decoder_pipeline(
        shots=shots,
        repeats=repeats,
        syndrome_rounds=syndrome_rounds,
        measurement_error_probability=0.0,
        seed=seed,
    )

    benchmark = run_decoder_noise_sweep(
        code_spec=repetition_code_3(),
        probabilities=probabilities,
        n_trials=benchmark_trials,
        n_rounds=syndrome_rounds,
        shots=shots,
        seed=seed,
    )

    return NoiseAwarePipelineResult(
        encoded_pipeline_result=encoded,
        decoder_benchmark_result=benchmark,
        metadata={
            "shots": shots,
            "repeats": repeats,
            "syndrome_rounds": syndrome_rounds,
            "benchmark_trials": benchmark_trials,
        },
    )
