# AZM-QOS v1.7 Circuit-Level QEC Benchmarks

v1.7 adds repeated syndrome-circuit benchmark scaffolding.

## New file

```text
azmqos_qec/circuit_benchmarks.py
```

## Main objects

```text
CircuitSyndromeRoundRecord
CircuitLevelSyndromeBenchmarkResult
CircuitLevelDecoderSweepResult
```

## Main functions

```text
counts_to_syndrome_bit
run_circuit_level_syndrome_benchmark
run_circuit_level_decoder_sweep
export_circuit_level_decoder_sweep_csv
make_circuit_level_decoder_sweep_report
```

## Modes

- If Qiskit Aer is installed and enabled, run noisy syndrome circuits.
- Otherwise use a circuit-noise scaffold probability model.

## Scientific limitation

This is still not a full fault-tolerant simulator. It is a benchmark layer designed to be extended with realistic circuit noise, repeated rounds, and decoder graph construction.
