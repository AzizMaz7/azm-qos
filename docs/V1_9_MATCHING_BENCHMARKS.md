# AZM-QOS v1.9 Matching Benchmarks

v1.9 adds detector-event matching benchmark scaffolds.

## New file

```text
azmqos_qec/matching_benchmarks.py
```

## Main functions

```text
run_matching_decoder_benchmark
export_matching_benchmark_csv
make_matching_benchmark_report
```

## Failure definition

The scaffold samples detector events and decodes them. If the decoder returns a boundary correction placeholder, the trial is counted as a logical failure.

This should later be replaced by a proper detector-error-model decoder and logical observable tracking.
