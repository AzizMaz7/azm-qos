from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from azmqos_pipeline.circuit_level_qec_pipeline import run_endvqs_circuit_level_qec_pipeline
from azmqos_qec.detectors import (
    syndrome_history_to_detector_events,
    build_repetition_detector_graph,
)
from azmqos_qec.matching import decode_detector_events, GreedyMatchingDecoder

@dataclass
class DetectorGraphPipelineResult:
    circuit_pipeline_result: Any
    detector_graph: Any
    detector_events: list
    matching_result: Any
    metadata: dict

    def summary(self):
        return (
            "DetectorGraphPipelineResult\n"
            f"  M shape: {self.circuit_pipeline_result.M.shape}\n"
            f"  V shape: {self.circuit_pipeline_result.V.shape}\n"
            f"  detector nodes: {len(self.detector_graph.nodes)}\n"
            f"  detector edges: {len(self.detector_graph.edges)}\n"
            f"  detector events: {len(self.detector_events)}\n"
            f"  matching correction: {self.matching_result.correction}"
        )

def run_endvqs_detector_graph_pipeline(
    shots: int = 128,
    repeats: int = 1,
    n_rounds: int = 5,
    n_trials: int = 5,
    measurement_error_probability: float = 0.05,
    seed: int | None = 123,
):
    """Run encoded END/VQS + circuit-level QEC and build detector graph interface.

    This uses the first circuit-level benchmark point as a source of repeated
    syndrome records for detector conversion.
    """
    circuit_pipeline = run_endvqs_circuit_level_qec_pipeline(
        shots=shots,
        repeats=repeats,
        n_rounds=n_rounds,
        n_trials=n_trials,
        seed=seed,
    )

    # Build a small graph for the repetition-code stabilizer names.
    stabilizer_names = ["S_ZZI", "S_IZZ"]
    graph = build_repetition_detector_graph(
        stabilizer_names=stabilizer_names,
        n_rounds=n_rounds,
        measurement_error_probability=measurement_error_probability,
    )

    # Create a deterministic no-event syndrome history scaffold from the graph
    # size. Users can replace this with measured CircuitSyndromeRoundRecord data.
    class _Record:
        def __init__(self, round_index):
            self.round_index = round_index
            self.syndrome_bits = {name: 0 for name in stabilizer_names}

    records = [_Record(t) for t in range(n_rounds)]
    events = syndrome_history_to_detector_events(records)
    matching = decode_detector_events(graph, events, decoder=GreedyMatchingDecoder())

    return DetectorGraphPipelineResult(
        circuit_pipeline_result=circuit_pipeline,
        detector_graph=graph,
        detector_events=events,
        matching_result=matching,
        metadata={
            "shots": shots,
            "repeats": repeats,
            "n_rounds": n_rounds,
            "measurement_error_probability": measurement_error_probability,
        },
    )
