from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import json
import math

@dataclass(frozen=True)
class DetectorNode:
    """A detector node indexed by stabilizer name and time/round."""

    node_id: str
    stabilizer_name: str
    round_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class DetectorEvent:
    """A detector event flags a change or nontrivial syndrome condition."""

    node: DetectorNode
    value: int
    source: str = "syndrome_difference"
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"DetectorEvent(node={self.node.node_id}, stabilizer={self.node.stabilizer_name}, "
            f"round={self.node.round_index}, value={self.value}, source={self.source})"
        )

@dataclass
class DetectorGraphEdge:
    """Weighted edge between detector nodes."""

    source: str
    target: str
    weight: float
    error_probability: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class DetectorGraph:
    """Simple detector graph for decoder interfaces."""

    nodes: dict[str, DetectorNode] = field(default_factory=dict)
    edges: list[DetectorGraphEdge] = field(default_factory=list)
    boundary_nodes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: DetectorNode):
        self.nodes[node.node_id] = node

    def add_edge(self, edge: DetectorGraphEdge):
        self.edges.append(edge)

    def summary(self):
        return (
            f"DetectorGraph(nodes={len(self.nodes)}, edges={len(self.edges)}, "
            f"boundaries={len(self.boundary_nodes)}, metadata={self.metadata})"
        )

    def to_dict(self):
        return {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "stabilizer_name": n.stabilizer_name,
                    "round_index": n.round_index,
                    "metadata": n.metadata,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "weight": e.weight,
                    "error_probability": e.error_probability,
                    "metadata": e.metadata,
                }
                for e in self.edges
            ],
            "boundary_nodes": list(self.boundary_nodes),
            "metadata": self.metadata,
        }

def detector_node_id(stabilizer_name: str, round_index: int) -> str:
    safe = stabilizer_name.replace(" ", "_")
    return f"{safe}@t{round_index}"

def syndrome_history_to_detector_events(round_records, include_initial: bool = True):
    """Convert repeated syndrome rounds into detector events.

    Detector convention:
    - initial event: syndrome bit at t=0 if nonzero
    - later event: syndrome bit changes between t-1 and t
    """
    events = []
    if not round_records:
        return events

    stabilizer_names = list(round_records[0].syndrome_bits.keys())
    previous = {name: 0 for name in stabilizer_names}

    for record in round_records:
        for name in stabilizer_names:
            current = int(record.syndrome_bits.get(name, 0))
            if record.round_index == 0 and not include_initial:
                previous[name] = current
                continue

            value = current if record.round_index == 0 else (current ^ previous[name])
            if value:
                node = DetectorNode(
                    node_id=detector_node_id(name, record.round_index),
                    stabilizer_name=name,
                    round_index=record.round_index,
                    metadata={"round_index": record.round_index},
                )
                events.append(
                    DetectorEvent(
                        node=node,
                        value=value,
                        metadata={"current": current, "previous": previous[name]},
                    )
                )
            previous[name] = current

    return events

def probability_to_weight(p: float, eps: float = 1e-12) -> float:
    """Convert probability to matching-style log-likelihood edge weight."""
    p = min(max(float(p), eps), 1.0 - eps)
    return math.log((1.0 - p) / p)

def build_repetition_detector_graph(
    stabilizer_names,
    n_rounds: int,
    measurement_error_probability: float = 0.01,
):
    """Build a simple spacetime detector graph for repetition-code style syndrome history.

    Edges:
    - time-like edges connecting same stabilizer across adjacent rounds
    - same-round neighbor edges connecting adjacent stabilizers
    - boundary edges from first/last round nodes to virtual boundary labels
    """
    if n_rounds <= 0:
        raise ValueError("n_rounds must be positive.")
    names = list(stabilizer_names)
    graph = DetectorGraph(metadata={
        "type": "repetition_detector_graph_scaffold",
        "n_rounds": n_rounds,
        "measurement_error_probability": measurement_error_probability,
    })

    for t in range(n_rounds):
        for name in names:
            graph.add_node(
                DetectorNode(
                    node_id=detector_node_id(name, t),
                    stabilizer_name=name,
                    round_index=t,
                )
            )

    w_meas = probability_to_weight(measurement_error_probability)

    # Time-like edges.
    for name in names:
        for t in range(n_rounds - 1):
            graph.add_edge(
                DetectorGraphEdge(
                    source=detector_node_id(name, t),
                    target=detector_node_id(name, t + 1),
                    weight=w_meas,
                    error_probability=measurement_error_probability,
                    metadata={"edge_type": "time_like_measurement"},
                )
            )

    # Space-like neighbor edges.
    for t in range(n_rounds):
        for i in range(len(names) - 1):
            graph.add_edge(
                DetectorGraphEdge(
                    source=detector_node_id(names[i], t),
                    target=detector_node_id(names[i + 1], t),
                    weight=w_meas,
                    error_probability=measurement_error_probability,
                    metadata={"edge_type": "space_like_neighbor"},
                )
            )

    # Boundary nodes are virtual labels, not normal detector nodes.
    for name in names:
        left = f"BOUNDARY_START_{name}"
        right = f"BOUNDARY_END_{name}"
        graph.boundary_nodes.extend([left, right])
        graph.add_edge(
            DetectorGraphEdge(
                source=left,
                target=detector_node_id(name, 0),
                weight=w_meas,
                error_probability=measurement_error_probability,
                metadata={"edge_type": "boundary_start"},
            )
        )
        graph.add_edge(
            DetectorGraphEdge(
                source=detector_node_id(name, n_rounds - 1),
                target=right,
                weight=w_meas,
                error_probability=measurement_error_probability,
                metadata={"edge_type": "boundary_end"},
            )
        )

    return graph

def save_detector_graph_json(graph: DetectorGraph, path):
    path = Path(path)
    path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")
    return path

def make_detector_graph_report(graph: DetectorGraph, events=None, output_path=None):
    events = events or []
    lines = [
        "# AZM-QOS v1.8 Detector Graph Report",
        "",
        "## Graph summary",
        "",
        "```text",
        graph.summary(),
        "```",
        "",
        "## Detector events",
        "",
    ]
    if events:
        for event in events:
            lines.extend(["```text", event.summary(), "```", ""])
    else:
        lines.append("No detector events were provided.")

    lines.extend([
        "",
        "## Edge table",
        "",
        "| source | target | weight | edge type |",
        "|---|---|---:|---|",
    ])
    for edge in graph.edges:
        lines.append(
            f"| {edge.source} | {edge.target} | {edge.weight:.6f} | "
            f"{edge.metadata.get('edge_type', '')} |"
        )

    text = "\n".join(lines)
    if output_path is not None:
        Path(output_path).write_text(text, encoding="utf-8")
    return text
