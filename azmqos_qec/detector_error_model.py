from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import json

from .detectors import DetectorGraph, DetectorGraphEdge, DetectorNode, DetectorEvent, probability_to_weight, syndrome_history_to_detector_events, build_repetition_detector_graph

@dataclass
class DetectorErrorInstruction:
    """Stim-like detector-error-model instruction scaffold."""

    probability: float
    detectors: list[str]
    logical_observables: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_text(self):
        targets = [f"D[{d}]" for d in self.detectors]
        targets += [f"L[{l}]" for l in self.logical_observables]
        return f"error({self.probability:.12g}) " + " ".join(targets)

@dataclass
class DetectorErrorModel:
    """Detector-error-model scaffold.

    This is inspired by detector error models used in modern QEC tools, but the
    v1.9 format is an AZM-QOS internal scaffold rather than a guaranteed Stim-compatible file.
    """

    instructions: list[DetectorErrorInstruction] = field(default_factory=list)
    detector_id_map: dict[str, int] = field(default_factory=dict)
    logical_observables: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"DetectorErrorModel(instructions={len(self.instructions)}, "
            f"detectors={len(self.detector_id_map)}, logicals={len(self.logical_observables)}, "
            f"metadata={self.metadata})"
        )

    def to_text(self):
        lines = [
            "# AZM-QOS detector error model scaffold",
            f"# detectors: {len(self.detector_id_map)}",
            f"# logicals: {len(self.logical_observables)}",
        ]
        for node_id, det_id in sorted(self.detector_id_map.items(), key=lambda x: x[1]):
            lines.append(f"detector D[{det_id}] # {node_id}")
        for logical_id, label in self.logical_observables.items():
            lines.append(f"logical_observable L[{logical_id}] # {label}")
        for instruction in self.instructions:
            # Convert node IDs into detector integer IDs for text form.
            det_ids = [str(self.detector_id_map[d]) for d in instruction.detectors if d in self.detector_id_map]
            converted = DetectorErrorInstruction(
                probability=instruction.probability,
                detectors=det_ids,
                logical_observables=instruction.logical_observables,
                metadata=instruction.metadata,
            )
            lines.append(converted.to_text())
        return "\n".join(lines)

    def to_dict(self):
        return {
            "detector_id_map": self.detector_id_map,
            "logical_observables": self.logical_observables,
            "instructions": [
                {
                    "probability": i.probability,
                    "detectors": i.detectors,
                    "logical_observables": i.logical_observables,
                    "metadata": i.metadata,
                }
                for i in self.instructions
            ],
            "metadata": self.metadata,
        }

def detector_graph_to_error_model(
    graph: DetectorGraph,
    default_probability: float = 0.01,
    logical_labels: dict[str, str] | None = None,
):
    """Convert DetectorGraph edges into a detector-error-model scaffold."""
    detector_id_map = {node_id: idx for idx, node_id in enumerate(sorted(graph.nodes.keys()))}
    logical_labels = logical_labels or {}

    instructions = []
    for edge in graph.edges:
        detectors = []
        if edge.source in detector_id_map:
            detectors.append(edge.source)
        if edge.target in detector_id_map:
            detectors.append(edge.target)

        logicals = []
        # Boundary edges can be interpreted as possible logical/boundary events.
        if edge.source in graph.boundary_nodes or edge.target in graph.boundary_nodes:
            for logical_id in logical_labels:
                if logical_id in edge.metadata.get("logical_tags", []) or not edge.metadata.get("logical_tags"):
                    logicals.append(logical_id)
                    break

        if detectors or logicals:
            instructions.append(
                DetectorErrorInstruction(
                    probability=edge.error_probability if edge.error_probability is not None else default_probability,
                    detectors=detectors,
                    logical_observables=logicals,
                    metadata={"edge_type": edge.metadata.get("edge_type", "")},
                )
            )

    return DetectorErrorModel(
        instructions=instructions,
        detector_id_map=detector_id_map,
        logical_observables=logical_labels,
        metadata={
            "source": "detector_graph_to_error_model",
            "graph_nodes": len(graph.nodes),
            "graph_edges": len(graph.edges),
        },
    )

def circuit_round_records_to_detector_error_model(
    round_records,
    stabilizer_names,
    measurement_error_probability: float = 0.01,
    logical_labels: dict[str, str] | None = None,
):
    """Build detector graph and detector-error model from syndrome round records."""
    n_rounds = len(round_records)
    graph = build_repetition_detector_graph(
        stabilizer_names=stabilizer_names,
        n_rounds=max(1, n_rounds),
        measurement_error_probability=measurement_error_probability,
    )
    events = syndrome_history_to_detector_events(round_records)
    model = detector_graph_to_error_model(
        graph,
        default_probability=measurement_error_probability,
        logical_labels=logical_labels or {"0": "logical_failure_placeholder"},
    )
    model.metadata["detector_events"] = len(events)
    return model, graph, events

def save_detector_error_model_text(model: DetectorErrorModel, path):
    path = Path(path)
    path.write_text(model.to_text(), encoding="utf-8")
    return path

def save_detector_error_model_json(model: DetectorErrorModel, path):
    path = Path(path)
    path.write_text(json.dumps(model.to_dict(), indent=2), encoding="utf-8")
    return path

def make_detector_error_model_report(model: DetectorErrorModel, graph=None, events=None, output_path=None):
    events = events or []
    lines = [
        "# AZM-QOS v1.9 Detector Error Model Report",
        "",
        "## Model summary",
        "",
        "```text",
        model.summary(),
        "```",
        "",
    ]
    if graph is not None:
        lines.extend([
            "## Graph summary",
            "",
            "```text",
            graph.summary(),
            "```",
            "",
        ])
    lines.extend([
        "## Detector events",
        "",
    ])
    if events:
        for event in events:
            lines.extend(["```text", event.summary(), "```", ""])
    else:
        lines.append("No detector events provided.")
    lines.extend([
        "",
        "## Detector error model text",
        "",
        "```text",
        model.to_text(),
        "```",
    ])
    text = "\n".join(lines)
    if output_path is not None:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
