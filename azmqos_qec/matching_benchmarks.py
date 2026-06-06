from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import csv
import numpy as np

from .detectors import build_repetition_detector_graph, DetectorNode, DetectorEvent
from .matching import decode_detector_events, GreedyMatchingDecoder, PyMatchingDecoderAdapter, pymatching_available
from .detector_error_model import detector_graph_to_error_model

@dataclass
class MatchingBenchmarkPoint:
    error_probability: float
    n_trials: int
    n_logical_failures: int
    logical_failure_rate: float
    decoder_name: str
    used_pymatching: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"MatchingBenchmarkPoint(p={self.error_probability:.6f}, trials={self.n_trials}, "
            f"failures={self.n_logical_failures}, rate={self.logical_failure_rate:.6f}, "
            f"decoder={self.decoder_name}, pymatching={self.used_pymatching})"
        )

@dataclass
class MatchingBenchmarkResult:
    code_name: str
    n_rounds: int
    points: list[MatchingBenchmarkPoint]
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        lines = [f"MatchingBenchmarkResult(code={self.code_name}, rounds={self.n_rounds})"]
        for point in self.points:
            lines.append(f"  {point.summary()}")
        return "\n".join(lines)

def _sample_detector_events(graph, error_probability: float, rng):
    events = []
    for node in graph.nodes.values():
        if rng.random() < error_probability:
            events.append(DetectorEvent(node=node, value=1, source="sampled_detector_noise"))
    return events

def run_matching_decoder_benchmark(
    stabilizer_names=None,
    n_rounds: int = 5,
    probabilities=None,
    n_trials: int = 100,
    seed: int | None = 123,
    use_pymatching_if_available: bool = False,
):
    """Benchmark matching decoder scaffold using sampled detector events.

    Failure definition:
    - Greedy decoder returns a boundary correction placeholder if an odd number
      of detector events are unmatched.
    - That is counted as logical failure in this scaffold.
    """
    if probabilities is None:
        probabilities = [0.0, 0.01, 0.02, 0.05, 0.10]
    stabilizer_names = stabilizer_names or ["S_ZZI", "S_IZZ"]
    rng = np.random.default_rng(seed)

    points = []
    for p in probabilities:
        graph = build_repetition_detector_graph(stabilizer_names, n_rounds, measurement_error_probability=p)
        detector_graph_to_error_model(graph, default_probability=p, logical_labels={"0": "logical_boundary"})
        decoder = PyMatchingDecoderAdapter() if use_pymatching_if_available else GreedyMatchingDecoder()
        failures = 0
        used_pm = False

        for _ in range(n_trials):
            events = _sample_detector_events(graph, p, rng)
            result = decode_detector_events(graph, events, decoder=decoder)
            used_pm = used_pm or bool(result.metadata.get("pymatching_available", False))
            if result.correction != "I":
                failures += 1

        points.append(
            MatchingBenchmarkPoint(
                error_probability=float(p),
                n_trials=n_trials,
                n_logical_failures=failures,
                logical_failure_rate=failures / n_trials,
                decoder_name=decoder.__class__.__name__,
                used_pymatching=used_pm and pymatching_available(),
                metadata={"stabilizers": stabilizer_names},
            )
        )

    return MatchingBenchmarkResult(
        code_name="repetition_detector_graph_scaffold",
        n_rounds=n_rounds,
        points=points,
        metadata={
            "benchmark_type": "sampled_detector_events",
            "pymatching_available": pymatching_available(),
        },
    )

def export_matching_benchmark_csv(result: MatchingBenchmarkResult, path):
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "code_name",
            "n_rounds",
            "error_probability",
            "n_trials",
            "n_logical_failures",
            "logical_failure_rate",
            "decoder_name",
            "used_pymatching",
        ])
        for point in result.points:
            writer.writerow([
                result.code_name,
                result.n_rounds,
                point.error_probability,
                point.n_trials,
                point.n_logical_failures,
                point.logical_failure_rate,
                point.decoder_name,
                point.used_pymatching,
            ])
    return path

def make_matching_benchmark_report(result: MatchingBenchmarkResult, output_path=None):
    lines = [
        "# AZM-QOS v1.9 Matching Decoder Benchmark Report",
        "",
        "```text",
        result.summary(),
        "```",
        "",
        "| detector error p | trials | logical failures | logical failure rate | decoder | PyMatching |",
        "|---:|---:|---:|---:|---|---|",
    ]
    for point in result.points:
        lines.append(
            f"| {point.error_probability:.6f} | {point.n_trials} | {point.n_logical_failures} | "
            f"{point.logical_failure_rate:.6f} | {point.decoder_name} | {point.used_pymatching} |"
        )
    lines.extend([
        "",
        "## Note",
        "",
        "This benchmark samples detector events directly. It is a scaffold for a future detector-error-model based matching benchmark.",
    ])
    text = "\n".join(lines)
    if output_path is not None:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
