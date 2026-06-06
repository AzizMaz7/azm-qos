# AZM-QOS v2.5 Final Validation Report

## Summary

- Tests run through v2.5: **23 / 23 passed**
- Safe examples run: **7 / 7 passed**
- Safe CLI checks run: **2 / 2 passed**
- Real IBM hardware jobs submitted: **0**

## Patch applied

During validation, I found and fixed one small CLI issue in `azmqos_research/cli.py`: local `from pathlib import Path` imports inside `main()` shadowed the top-level `Path` import, causing `UnboundLocalError` for earlier CLI branches such as `azmqos run` and `azmqos real-terms`. The final package has this fixed.

## Test coverage

The accumulated test suite from core/v0.4 through v2.5 was run in chunks:

```text
test_core_v04.py ... test_core_v09.py
test_v1_0_pipeline.py ... test_v1_9_detector_error_model.py
test_v2_0_research_platform.py
test_v2_1_real_terms_workflow.py
test_v2_2_publication_plots.py
test_v2_3_ibm_runtime_path.py
test_v2_4_hardware_comparison.py
test_v2_4_updated_ibm_results_helper.py
test_v2_5_calibration_mitigation.py
```

All passed after the CLI patch.

## Safe examples checked

```text
hardware_result_parsing_demo.py
hardware_comparison_report_demo.py
backend_snapshot_demo.py
compare_saved_counts_demo.py
readout_mitigation_demo.py
zne_demo.py
mitigated_hardware_comparison_demo.py
```

All passed.

## Safe CLI checks

```text
python -m azmqos_research.cli hardware-compare --output-dir outputs/final_validation_hardware
python -m azmqos_research.cli mitigate --output-dir outputs/final_validation_mitigate
```

Both returned code `0`. Runtime warnings from `runpy` are harmless in this context and do not affect output generation.

## Hardware safety

No command with `--submit` was run. No IBM hardware job was submitted.
