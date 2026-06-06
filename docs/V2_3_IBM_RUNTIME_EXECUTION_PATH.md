# AZM-QOS v2.3 IBM Runtime Execution Path

v2.3 adds the IBM Runtime hardware-execution layer.

## New file

```text
azmqos_research/ibm_runtime.py
```

## Main features

- IBM Runtime diagnostics
- Backend listing and filtering
- Least-busy backend selection
- ISA-circuit preparation
- SamplerV2 submission helper
- EstimatorV2 submission helper
- Dry-run safety by default
- IBM Runtime reports

## CLI

```bash
azmqos ibm-diagnose
azmqos ibm-dry-run --backend ibm_brisbane --shots 1024
```

To actually submit a job:

```bash
azmqos ibm-dry-run --backend ibm_brisbane --shots 1024 --submit
```

Use real submission only after confirming your IBM account, backend access, and expected cost/usage.
