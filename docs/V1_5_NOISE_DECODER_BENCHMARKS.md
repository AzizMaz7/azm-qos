# AZM-QOS v1.5 Noise-Aware Decoder Benchmarks

v1.5 adds measurement-noise sweeps and decoder benchmark reports.

## New files

```text
azmqos_qec/noise_models.py
azmqos_qec/decoder_benchmarks.py
azmqos_pipeline/noise_aware_pipeline.py
```

## Main functions

```text
run_decoder_noise_sweep
export_decoder_benchmark_csv
make_decoder_benchmark_report
run_noise_aware_endvqs_qec_pipeline
```

## Failure definition

For the v1.5 scaffold, no data error is intentionally inserted. Therefore the expected correction is `I`.

A trial fails if:

```text
decoder_result.correction != I
```

## Limitations

This is not yet a threshold simulation. It only models syndrome measurement-bit flips.
