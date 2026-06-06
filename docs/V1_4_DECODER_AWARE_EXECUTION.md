# AZM-QOS v1.4 Decoder-Aware Execution

v1.4 adds decoder-aware QEC execution.

## New file

```text
azmqos_qec/decoder_execution.py
```

## Main objects

```text
CorrectionHistoryEntry
DecoderAwareExecutionResult
```

## Main function

```text
run_decoder_aware_qec_execution
```

## Pipeline integration

```text
azmqos_pipeline/logical_decoder_pipeline.py
```

connects:

```text
END/VQS encoded workloads
+
repeated syndrome rounds
+
decoder decision
```

into a single demonstration.
