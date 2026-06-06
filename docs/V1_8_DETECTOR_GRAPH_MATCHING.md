# AZM-QOS v1.8 Detector Graph and Matching Interface

v1.8 adds detector-event graph scaffolding.

## New files

```text
azmqos_qec/detectors.py
azmqos_qec/matching.py
azmqos_pipeline/detector_graph_pipeline.py
```

## Detector concepts

```text
DetectorNode
DetectorEvent
DetectorGraphEdge
DetectorGraph
```

## Decoder concepts

```text
MatchingDecoderInterface
GreedyMatchingDecoder
PyMatchingDecoderAdapter
```

## Example

```python
graph = build_repetition_detector_graph(["S_ZZI", "S_IZZ"], n_rounds=5)
events = syndrome_history_to_detector_events(round_records)
result = decode_detector_events(graph, events)
```

## Scientific limitation

This is not yet a full detector error model for a surface code or LDPC code. It is the interface layer needed before adding PyMatching or other decoders.
