# AZM-QOS v1.9 Detector Error Model

v1.9 adds detector-error-model export scaffolding.

## New file

```text
azmqos_qec/detector_error_model.py
```

## Main objects

```text
DetectorErrorInstruction
DetectorErrorModel
```

## Main functions

```text
detector_graph_to_error_model
save_detector_error_model_text
save_detector_error_model_json
make_detector_error_model_report
```

## Format note

The `.dem.txt` export is Stim-like, but not guaranteed to be fully Stim-compatible yet.
