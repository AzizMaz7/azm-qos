from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import itertools

from .detectors import DetectorEvent, DetectorGraph

def pymatching_available() -> bool:
    try:
        import pymatching  # noqa: F401
        return True
    except Exception:
        return False

@dataclass
class MatchingDecoderResult:
    correction: str
    matched_pairs: list[tuple[str, str]]
    unmatched_events: list[str]
    used_external_decoder: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self):
        return (
            f"MatchingDecoderResult(correction={self.correction}, "
            f"pairs={len(self.matched_pairs)}, unmatched={len(self.unmatched_events)}, "
            f"external={self.used_external_decoder})"
        )

class MatchingDecoderInterface:
    def decode(self, graph: DetectorGraph, events: list[DetectorEvent]) -> MatchingDecoderResult:
        raise NotImplementedError

class GreedyMatchingDecoder(MatchingDecoderInterface):
    """Simple greedy matching scaffold.

    It pairs detector events in sorted order. This is not minimum-weight perfect
    matching, but it validates the graph-decoder interface.
    """

    def decode(self, graph: DetectorGraph, events: list[DetectorEvent]) -> MatchingDecoderResult:
        event_ids = sorted(e.node.node_id for e in events if e.value)
        pairs = []
        unmatched = []

        it = iter(event_ids)
        for first in it:
            second = next(it, None)
            if second is None:
                unmatched.append(first)
            else:
                pairs.append((first, second))

        correction = "I" if not unmatched else "boundary_correction_placeholder"
        return MatchingDecoderResult(
            correction=correction,
            matched_pairs=pairs,
            unmatched_events=unmatched,
            used_external_decoder=False,
            metadata={"decoder": "GreedyMatchingDecoder", "graph_edges": len(graph.edges)},
        )

class PyMatchingDecoderAdapter(MatchingDecoderInterface):
    """Optional PyMatching adapter scaffold.

    This class checks availability and falls back to GreedyMatchingDecoder unless
    full detector-error-model construction is implemented.
    """

    def __init__(self, fallback=True):
        self.fallback = fallback

    def decode(self, graph: DetectorGraph, events: list[DetectorEvent]) -> MatchingDecoderResult:
        if not pymatching_available():
            if self.fallback:
                result = GreedyMatchingDecoder().decode(graph, events)
                result.metadata["pymatching_available"] = False
                result.metadata["fallback"] = True
                return result
            raise ImportError("PyMatching is not installed. Install with: python -m pip install pymatching")

        # Full PyMatching detector-error-model conversion is intentionally left
        # as a future implementation. For now, return a marked greedy result.
        result = GreedyMatchingDecoder().decode(graph, events)
        result.used_external_decoder = False
        result.metadata["pymatching_available"] = True
        result.metadata["note"] = "PyMatching available, but full graph conversion is not implemented in v1.8."
        return result

def decode_detector_events(graph: DetectorGraph, events: list[DetectorEvent], decoder=None):
    decoder = decoder or GreedyMatchingDecoder()
    return decoder.decode(graph, events)
